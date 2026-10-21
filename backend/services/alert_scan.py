"""Location alerts for coverage gaps, missing qualifications, expected shortages, and
training due (BR10), plus schedules not plotted far enough ahead and vacation not yet
in the schedule. Compliance and maintenance alerts are written where they happen."""

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import (
    Alert,
    Assignment,
    MroDemand,
    MroLocation,
    RepUnavailability,
    TechRep,
)
from schemas import AlertScanResult
from services import leave, training
from services.compliance import SEVEN_ON_SEVEN_OFF, Availability, is_certified
from services.dates import week_start
from services.scheduler import _hours_by_local_date, _tz, active_rules, home_tz

SCAN_TYPES = (
    "coverage_gap",
    "no_qualified_rep",
    "shortage",
    "training_due",
    "schedule_horizon",
    "vacation_unused",
)
# Rechecked in full on every scan, whatever the window.
REP_TYPES = ("training_due", "schedule_horizon", "vacation_unused")
# Gaps starting this soon are critical.
URGENT = timedelta(days=7)

Key = tuple[str, int | None, int | None, int | None, str]


def _key(a: Alert) -> Key:
    return (a.alert_type, a.mro_id, a.rep_id, a.demand_id, a.message)


def scan(
    db: Session, start: datetime, end: datetime, training_days: int
) -> AlertScanResult:
    """Raise alerts for [start, end) and acknowledge earlier ones that no longer apply."""
    mros = {m.id: m for m in db.scalars(select(MroLocation))}
    reps = list(
        db.scalars(
            select(TechRep)
            .where(TechRep.active)
            .options(
                selectinload(TechRep.certifications),
                selectinload(TechRep.shift_pattern),
            )
        )
    )
    in_window = list(
        db.scalars(
            select(MroDemand).where(
                MroDemand.end_time > start, MroDemand.start_time < end
            )
        )
    )
    demands = [d for d in in_window if d.status != "cancelled"]
    filled = Counter(
        db.scalars(
            select(Assignment.demand_id).where(
                Assignment.demand_id.in_([d.id for d in demands]),
                Assignment.status != "cancelled",
            )
        )
    )
    found: dict[Key, Alert] = {}

    def add(alert: Alert) -> None:
        found[_key(alert)] = alert

    now = datetime.now(start.tzinfo)
    for d in demands:
        short = d.reps_needed - filled[d.id]
        if short <= 0 or d.status != "open":
            continue
        mro = mros[d.mro_id]
        day = d.start_time.astimezone(_tz(mro.timezone)).date()
        last = d.end_time.astimezone(_tz(mro.timezone)).date()
        if not any(is_certified(r, d.aircraft_type_id, day, last) for r in reps):
            add(
                Alert(
                    alert_type="no_qualified_rep",
                    severity="critical",
                    mro_id=d.mro_id,
                    demand_id=d.id,
                    message=f"{mro.facility_name} on {day}: no active rep holds a valid "
                    f"certification for demand {d.id}",
                )
            )
            continue
        add(
            Alert(
                alert_type="coverage_gap",
                severity="critical" if d.start_time - now < URGENT else "warning",
                mro_id=d.mro_id,
                demand_id=d.id,
                message=f"{mro.facility_name} on {day}: demand {d.id} is short {short} of "
                f"{d.reps_needed} rep(s)",
            )
        )

    # Expected shortage: more reps needed on a day than qualified reps not on leave.
    avail = Availability(db, start, end)
    need: dict[tuple[int, date], int] = Counter()
    types: dict[tuple[int, date], set[int]] = defaultdict(set)
    for d in demands:
        day = d.start_time.astimezone(_tz(mros[d.mro_id].timezone)).date()
        need[d.mro_id, day] += d.reps_needed
        types[d.mro_id, day].add(d.aircraft_type_id)
    worst: dict[tuple[int, date], tuple[int, int, date]] = {}
    for (mro_id, day), n in need.items():
        tz = _tz(mros[mro_id].timezone)
        day_start = datetime.combine(day, datetime.min.time(), tz)
        day_end = day_start + timedelta(days=1)
        pool = sum(
            1
            for r in reps
            if any(is_certified(r, t, day, day) for t in types[mro_id, day])
            and not any(s < day_end and day_start < e for s, e, _ in avail.leave[r.id])
        )
        week = (mro_id, week_start(day))
        if n > pool and (
            week not in worst or n - pool > worst[week][0] - worst[week][1]
        ):
            worst[week] = (n, pool, day)
    for (mro_id, monday), (n, pool, day) in worst.items():
        add(
            Alert(
                alert_type="shortage",
                severity="warning",
                mro_id=mro_id,
                message=f"Week of {monday} at {mros[mro_id].facility_name}: {n} reps "
                f"needed on {day}, {pool} qualified and not on leave",
            )
        )

    for item in training.due(db, training_days):
        expiry = (
            "never completed"
            if item.expires_on is None
            else f"expired on {item.expires_on}"
            if item.days_left < 0
            else f"expires on {item.expires_on}"
        )
        add(
            Alert(
                alert_type="training_due",
                severity="critical"
                if item.days_left is None or item.days_left < 0
                else "info",
                rep_id=item.rep_id,
                message=f"{item.rep_name}: {item.training_type_name} {expiry}",
            )
        )

    for alert in _unplotted(db, reps, mros) + _unscheduled_vacation(db, reps, mros):
        add(alert)

    # Earlier alerts are in scope when this scan rechecked the same demand, week, or
    # rep-level list, so a fixed problem gets acknowledged.
    scanned_demands = {d.id for d in in_window}
    first, last = week_start(start.date()), week_start(end.date())
    scanned_weeks = tuple(
        f"Week of {first + timedelta(weeks=i)} "
        for i in range((last - first).days // 7 + 1)
    )
    created = resolved = 0
    for old in db.scalars(
        select(Alert).where(~Alert.acknowledged, Alert.alert_type.in_(SCAN_TYPES))
    ):
        key = _key(old)
        if key in found:
            del found[key]
            continue
        in_scope = (
            old.alert_type in REP_TYPES
            or old.demand_id in scanned_demands
            or (old.alert_type == "shortage" and old.message.startswith(scanned_weeks))
        )
        if in_scope:
            old.acknowledged = True
            resolved += 1
    for alert in found.values():
        db.add(alert)
        created += 1
    db.commit()
    return AlertScanResult(created=created, resolved=resolved)


def _unplotted(
    db: Session, reps: list[TechRep], mros: dict[int, MroLocation]
) -> list[Alert]:
    """7-on/7-off reps with shift days in the next schedule_publish_days that have no
    assignment, leave, or training yet."""
    today = datetime.now(UTC).date()
    rules = active_rules(db, today)
    if rules is None:
        return []
    horizon = today + timedelta(days=rules.schedule_publish_days)
    lo = datetime.combine(today, datetime.min.time(), UTC) - timedelta(days=1)
    hi = datetime.combine(horizon, datetime.min.time(), UTC) + timedelta(days=2)
    planned: dict[int, set[date]] = defaultdict(set)
    for a in db.scalars(
        select(Assignment).where(
            Assignment.status != "cancelled",
            Assignment.end_time > lo,
            Assignment.start_time < hi,
        )
    ):
        planned[a.rep_id] |= set(
            _hours_by_local_date(a.start_time, a.end_time, _tz(mros[a.mro_id].timezone))
        )
    leave_rows = list(
        db.scalars(
            select(RepUnavailability).where(
                RepUnavailability.status == "approved",
                RepUnavailability.end_time > lo,
                RepUnavailability.start_time < hi,
            )
        )
    )
    out: list[Alert] = []
    for rep in reps:
        if (
            rep.shift_pattern_code != SEVEN_ON_SEVEN_OFF
            or rep.shift_cycle_start is None
        ):
            continue
        tz = home_tz(rep, mros.values())
        days = set(planned[rep.id])
        for u in leave_rows:
            if u.rep_id == rep.id:
                days |= leave.leave_dates(u, tz)
        missing = [
            d
            for d in (
                today + timedelta(days=i) for i in range((horizon - today).days + 1)
            )
            if leave.is_work_day(rep, d) and d not in days
        ]
        if missing:
            out.append(
                Alert(
                    alert_type="schedule_horizon",
                    severity="critical" if missing[0] - today < URGENT else "warning",
                    rep_id=rep.id,
                    message=f"{rep.name}: {len(missing)} shift day(s) in the next "
                    f"{rules.schedule_publish_days} days not plotted, from {missing[0]}",
                )
            )
    return out


def _unscheduled_vacation(
    db: Session, reps: list[TechRep], mros: dict[int, MroLocation]
) -> list[Alert]:
    """Reps whose vacation and stat days are not all in the schedule. Bids for a year
    close at the end of November before it, and days not used by December 31 are lost."""
    today = datetime.now(UTC).date()
    years = [today.year] + ([today.year + 1] if today.month == 12 else [])
    out: list[Alert] = []
    for rep in reps:
        tz = home_tz(rep, mros.values())
        for year in years:
            total = leave.biddable_days(db, rep.id, year)
            if not total:
                continue
            taken = leave.work_days(
                rep, leave.approved_leave(db, rep.id, "vacation", year), tz, year
            )
            left = total - len(taken)
            if left <= 0:
                continue
            deadline = (
                f"unused days are lost after December 31, {year}"
                if year == today.year
                else f"bids were due by November 30, {year - 1}"
            )
            out.append(
                Alert(
                    alert_type="vacation_unused",
                    severity="critical" if today.month == 12 else "warning",
                    rep_id=rep.id,
                    message=f"{rep.name}: {left:g} of {total:g} vacation and stat days "
                    f"for {year} not in the schedule; {deadline}",
                )
            )
    return out
