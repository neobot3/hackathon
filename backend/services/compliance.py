"""Checks a rep's schedule against CBA and company limits (BR6) and records alerts.

Findings are warnings: callers keep the change and report what it breaks.
"""

import calendar
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta, tzinfo
from itertools import pairwise

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from models import (
    AircraftType,
    Alert,
    Assignment,
    CbaRules,
    DemandResponse,
    LeaveBalance,
    MaintenanceEvent,
    MroDemand,
    MroLocation,
    RepTraining,
    RepUnavailability,
    SickLeaveAllowance,
    TechRep,
    TrainingType,
    VacationBid,
)
from schemas import ComplianceWarning
from services import leave
from services.scheduler import (
    _hours_by_local_date,
    _is_field_service,
    _is_pattern_work_day,
    _tz,
    active_rules,
    home_tz,
    seniority_key,
)

SEVEN_ON_SEVEN_OFF = "7-7"
# Context loaded either side of the checked window, for rest and rotation checks.
MARGIN = timedelta(days=21)
COMPLIANCE_TYPES = (
    "rest",
    "shift_pattern",
    "training_conflict",
    "training_expired",
    "vacation_limit",
    "sick_limit",
    "qualification",
    "seniority",
    "no_aircraft",
)
# Demand types that are not tied to an aircraft in the Heavy Maintenance Schedule.
UNSCHEDULED_DEMANDS = ("base_coverage", "aog")
LEAVE_CONFLICT_TYPE = {
    "training": "training_conflict",
    "vacation": "vacation_limit",
    "sick": "sick_limit",
}


def is_certified(rep: TechRep, aircraft_type_id: int, first: date, last: date) -> bool:
    return any(
        c.aircraft_type_id == aircraft_type_id
        and (c.certified_on is None or c.certified_on <= first)
        and (c.expires_on is None or c.expires_on >= last)
        for c in rep.certifications
    )


class Availability:
    """Approved leave, approved training, and live assignments around a window."""

    def __init__(self, db: Session, start: datetime, end: datetime) -> None:
        lo, hi = start - timedelta(days=2), end + timedelta(days=2)
        self.leave: dict[int, list[tuple[datetime, datetime, str]]] = defaultdict(list)
        self.booked: dict[int, list[tuple[int, datetime, datetime]]] = defaultdict(list)
        for u in db.scalars(
            select(RepUnavailability).where(
                RepUnavailability.status == "approved",
                RepUnavailability.end_time > lo,
                RepUnavailability.start_time < hi,
            )
        ):
            self.leave[u.rep_id].append(
                (u.start_time, u.end_time, f"on approved {u.reason}")
            )
        # Approved training normally has its own leave row; this covers any without one.
        for t in db.scalars(
            select(RepTraining).where(
                RepTraining.status == "approved",
                RepTraining.unavailability_id.is_(None),
                RepTraining.scheduled_end > lo,
                RepTraining.scheduled_start < hi,
            )
        ):
            self.leave[t.rep_id].append(
                (t.scheduled_start, t.scheduled_end, "in approved training")
            )
        for a in db.scalars(
            select(Assignment).where(
                Assignment.status != "cancelled",
                Assignment.end_time > lo,
                Assignment.start_time < hi,
            )
        ):
            travel = timedelta(hours=float(a.travel_hours))
            self.booked[a.rep_id].append(
                (a.id, a.start_time - travel, a.end_time + travel)
            )

    def reason(
        self,
        rep_id: int,
        start: datetime,
        end: datetime,
        rest: timedelta,
        ignore: Iterable[int] = (),
    ) -> str | None:
        """Why the rep cannot take [start, end), or None when they are free."""
        for s, e, why in self.leave[rep_id]:
            if s < end and start < e:
                return why
        skip = set(ignore)
        for assignment_id, s, e in self.booked[rep_id]:
            if assignment_id not in skip and s - rest < end and start < e + rest:
                return "already booked or short of minimum rest"
        return None


class _Findings:
    def __init__(self, rep: TechRep) -> None:
        self.rep = rep
        self.items: dict[tuple[str, int | None, str], ComplianceWarning] = {}

    def add(
        self, alert_type: str, severity: str, message: str, a: Assignment | None = None
    ) -> None:
        key = (alert_type, a.id if a else None, message)
        self.items[key] = ComplianceWarning(
            alert_type=alert_type,
            severity=severity,
            message=message[:500],
            rep_id=self.rep.id,
            mro_id=a.mro_id if a else None,
            demand_id=a.demand_id if a else None,
            assignment_id=a.id if a else None,
        )


def check_rep(
    db: Session, rep_id: int, start: datetime, end: datetime
) -> tuple[list[ComplianceWarning], set[int], set[int]]:
    """Findings for one rep around [start, end), the assignment IDs checked, and the
    years whose leave limits were checked."""
    rep = db.get(
        TechRep,
        rep_id,
        options=[
            selectinload(TechRep.certifications),
            selectinload(TechRep.shift_pattern),
        ],
    )
    if rep is None:
        return [], set(), set()
    rules = active_rules(db, start.date())
    lo, hi = start - MARGIN, end + MARGIN
    mros = {m.id: m for m in db.scalars(select(MroLocation))}
    rows = list(
        db.scalars(
            select(Assignment)
            .where(
                Assignment.rep_id == rep.id,
                Assignment.end_time > lo,
                Assignment.start_time < hi,
            )
            .order_by(Assignment.start_time)
        )
    )
    live = [a for a in rows if a.status != "cancelled"]
    found = _Findings(rep)

    def busy(a: Assignment) -> tuple[datetime, datetime]:
        travel = timedelta(hours=float(a.travel_hours))
        return a.start_time - travel, a.end_time + travel

    def local_days(a: Assignment) -> list[date]:
        return sorted(
            _hours_by_local_date(a.start_time, a.end_time, _tz(mros[a.mro_id].timezone))
        )

    # Minimum rest between shifts (19-1, 21-1).
    if rules is not None:
        rest = float(rules.min_rest_hours)
        field_rest = float(max(rules.min_rest_hours, rules.post_field_rest_hours))
        ordered = sorted(live, key=lambda a: busy(a)[0])
        for prev, cur in pairwise(ordered):
            gap = (busy(cur)[0] - busy(prev)[1]).total_seconds() / 3600
            field = _is_field_service(rep, mros[prev.mro_id]) or _is_field_service(
                rep, mros[cur.mro_id]
            )
            need = field_rest if field else rest
            if gap < need:
                found.add(
                    "rest",
                    "critical",
                    f"{rep.name}: {max(gap, 0):.1f} h rest before assignment {cur.id} "
                    f"on {local_days(cur)[0]}, under the {need:g} h minimum",
                    cur,
                )

    # Runs of consecutive worked days (rotations) and the days off between them.
    first_on: dict[date, Assignment] = {}
    for a in live:
        for day in local_days(a):
            first_on.setdefault(day, a)
    runs: list[list[date]] = []
    for day in sorted(first_on):
        if runs and (day - runs[-1][1]).days == 1:
            runs[-1][1] = day
        else:
            runs.append([day, day])
    if rules is not None:
        for (_, last), (nxt, _) in pairwise(runs):
            off = (nxt - last).days - 1
            if off < rules.min_days_off_between_rotations:
                found.add(
                    "rest",
                    "warning",
                    f"{rep.name}: {off} day(s) off before the rotation starting {nxt}, "
                    f"under the {rules.min_days_off_between_rotations}-day minimum",
                    first_on[nxt],
                )
        for first, last in runs:
            length = (last - first).days + 1
            if length > rules.max_consecutive_worked_days:
                found.add(
                    "rest",
                    "critical",
                    f"{rep.name}: {length} days in a row from {first}, over the "
                    f"{rules.max_consecutive_worked_days}-day limit",
                    first_on[first],
                )

    # 7-on/7-off: at most 7 days in a row, and no work on the pattern's days off.
    if rep.shift_pattern_code == SEVEN_ON_SEVEN_OFF:
        for first, last in runs:
            length = (last - first).days + 1
            if length > 7:
                found.add(
                    "shift_pattern",
                    "warning",
                    f"{rep.name}: {length} days in a row from {first} breaks 7-on/7-off",
                    first_on[first],
                )
        flagged: set[int] = set()
        for day, a in sorted(first_on.items()):
            if _is_pattern_work_day(rep, day) is False and a.id not in flagged:
                flagged.add(a.id)
                found.add(
                    "shift_pattern",
                    "warning",
                    f"{rep.name}: assignment {a.id} on {day} falls on a 7-on/7-off day off",
                    a,
                )

    # Assignments overlapping approved leave or training.
    window_leave = list(
        db.scalars(
            select(RepUnavailability).where(
                RepUnavailability.rep_id == rep.id,
                RepUnavailability.status == "approved",
                RepUnavailability.end_time > lo,
                RepUnavailability.start_time < hi,
            )
        )
    )
    window_training = list(
        db.scalars(
            select(RepTraining)
            .options(selectinload(RepTraining.training_type))
            .where(
                RepTraining.rep_id == rep.id,
                RepTraining.status == "approved",
                RepTraining.unavailability_id.is_(None),
                RepTraining.scheduled_end > lo,
                RepTraining.scheduled_start < hi,
            )
        )
    )
    for a in live:
        s, e = busy(a)
        for u in window_leave:
            kind = LEAVE_CONFLICT_TYPE.get(u.reason)
            if kind and u.start_time < e and s < u.end_time:
                found.add(
                    kind,
                    "critical",
                    f"{rep.name}: assignment {a.id} on {local_days(a)[0]} overlaps approved "
                    f"{u.reason}",
                    a,
                )
        for t in window_training:
            if t.scheduled_start < e and s < t.scheduled_end:
                found.add(
                    "training_conflict",
                    "critical",
                    f"{rep.name}: assignment {a.id} on {local_days(a)[0]} overlaps approved "
                    f"{t.training_type.name} training",
                    a,
                )

    tz = home_tz(rep, mros.values())
    training_spans = [
        (u.start_time, u.end_time) for u in window_leave if u.reason == "training"
    ] + [(t.scheduled_start, t.scheduled_end) for t in window_training]
    training_days = {
        d for s, e in training_spans for d in _hours_by_local_date(s, e, tz)
    }
    if _is_pattern_work_day(rep, start.date()) is not None:
        _check_days_off(rep, rules, start, end, tz, first_on, training_days, found)
        _check_training_in_rotation(rep, training_spans, tz, found)
    _check_aircraft_in_maintenance(db, rep, live, mros, local_days, found)

    # Mandatory training must be current for each assignment.
    mandatory = list(db.scalars(select(TrainingType).where(TrainingType.is_mandatory)))
    if mandatory and live:
        completed = list(
            db.scalars(
                select(RepTraining).where(
                    RepTraining.rep_id == rep.id, RepTraining.completed_on.is_not(None)
                )
            )
        )
        for t in mandatory:
            records = [r for r in completed if r.training_type_id == t.id]
            if not records:
                found.add(
                    "training_expired",
                    "warning",
                    f"{rep.name}: no completed {t.name} on record",
                    live[0],
                )
                continue
            if any(r.expires_on is None for r in records):
                continue
            expiry = max(r.expires_on for r in records)
            late = next((a for a in live if local_days(a)[-1] > expiry), None)
            if late is not None:
                found.add(
                    "training_expired",
                    "critical",
                    f"{rep.name}: {t.name} expired on {expiry}, before assignment {late.id} "
                    f"on {local_days(late)[0]}",
                    late,
                )

    # Qualification for the aircraft type.
    type_names = {t.id: t.model_name for t in db.scalars(select(AircraftType))}
    for a in live:
        if a.aircraft_type_id is None:
            continue
        days = local_days(a)
        if not is_certified(rep, a.aircraft_type_id, days[0], days[-1]):
            found.add(
                "qualification",
                "critical",
                f"{rep.name} has no valid {type_names.get(a.aircraft_type_id, 'aircraft type')} "
                f"certification for assignment {a.id} on {days[0]}",
                a,
            )

    # Vacation and sick leave limits for each year the window touches.
    years = range(start.astimezone(UTC).year, end.astimezone(UTC).year + 1)
    allowance = {
        s.month: float(s.max_days) for s in db.scalars(select(SickLeaveAllowance))
    }
    for year in years:
        vacation_days = leave.work_days(
            rep, leave.approved_leave(db, rep.id, "vacation", year), tz, year
        )
        sick_days = leave.work_days(
            rep, leave.approved_leave(db, rep.id, "sick", year), tz, year
        )
        for leave_type, taken, alert_type in (
            ("vacation", vacation_days, "vacation_limit"),
            ("sick", sick_days, "sick_limit"),
        ):
            if leave_type == "vacation":
                entitled = leave.biddable_days(db, rep.id, year)
                label = "vacation and stat"
            else:
                balance = db.get(LeaveBalance, (rep.id, year, leave_type))
                entitled = None if balance is None else float(balance.entitled_days)
                label = leave_type
            if entitled is not None and len(taken) > entitled:
                found.add(
                    alert_type,
                    "warning",
                    f"{rep.name}: {len(taken)} {leave_type} days approved in {year}, over the "
                    f"{entitled:g} {label} days entitled",
                )
        for month in range(1, 13):
            from_month = sum(1 for d in sick_days if d.month >= month)
            if month in allowance and from_month > allowance[month]:
                found.add(
                    "sick_limit",
                    "warning",
                    f"{rep.name}: {from_month} sick days from {calendar.month_name[month]} "
                    f"{year} to year end, over the {allowance[month]:g} allowed",
                )
                break

    # Company-wide cap on reps on vacation in the same week.
    if rules is not None:
        weeks = leave.vacation_weeks(db, date(years[0], 1, 1), date(years[-1], 12, 31))
        for monday, reps_off in sorted(weeks.items()):
            if rep.id in reps_off and len(reps_off) > rules.max_reps_off_per_week:
                found.add(
                    "vacation_limit",
                    "warning",
                    f"Week of {monday}: {len(reps_off)} reps on approved vacation, over the "
                    f"limit of {rules.max_reps_off_per_week}",
                )

    _check_seniority(db, rep, live, rules, found, years)

    return list(found.items.values()), {a.id for a in rows}, set(years)


def _pattern_run(rep: TechRep, day: date) -> tuple[date, date]:
    """First and last day of the run of pattern work days, or days off, around `day`."""
    kind = _is_pattern_work_day(rep, day)
    limit = len(rep.shift_pattern.cycle)
    first = last = day
    for _ in range(limit):
        if _is_pattern_work_day(rep, first - timedelta(days=1)) != kind:
            break
        first -= timedelta(days=1)
    for _ in range(limit):
        if _is_pattern_work_day(rep, last + timedelta(days=1)) != kind:
            break
        last += timedelta(days=1)
    return first, last


def _check_days_off(
    rep: TechRep,
    rules: CbaRules | None,
    start: datetime,
    end: datetime,
    tz: tzinfo,
    first_on: dict[date, Assignment],
    training_days: set[date],
    found: "_Findings",
) -> None:
    """Each set of pattern days off keeps min_hours_off_per_set free. The free days need
    not be consecutive: overtime or training may take some of them."""
    if rules is None:
        return
    need = float(rules.min_hours_off_per_set)
    day = _pattern_run(rep, start.astimezone(tz).date())[0]
    last_day = _pattern_run(rep, end.astimezone(tz).date())[1]
    while day <= last_day:
        first, last = _pattern_run(rep, day)
        day = last + timedelta(days=1)
        if _is_pattern_work_day(rep, first):
            continue
        days_off = [first + timedelta(days=i) for i in range((last - first).days + 1)]
        worked = [d for d in days_off if d in first_on or d in training_days]
        hours = 24 * (len(days_off) - len(worked))
        if worked and hours < need:
            found.add(
                "rest",
                "warning",
                f"{rep.name}: {hours} h free in the days off from {first} to {last}, "
                f"under the {need:g} h minimum",
                next((first_on[d] for d in worked if d in first_on), None),
            )


def _check_training_in_rotation(
    rep: TechRep,
    spans: list[tuple[datetime, datetime]],
    tz: tzinfo,
    found: "_Findings",
) -> None:
    """Training on shift must take the first or last day of the rotation. In the middle
    the rep would have to leave the MRO and fly back."""
    for s, e in spans:
        days = sorted(_hours_by_local_date(s, e, tz))
        rotations = {_pattern_run(rep, d) for d in days if _is_pattern_work_day(rep, d)}
        for first, last in sorted(rotations):
            if first not in days and last not in days:
                found.add(
                    "training_conflict",
                    "warning",
                    f"{rep.name}: training from {days[0]} to {days[-1]} falls mid-rotation "
                    f"({first} to {last}); on shift it must start or end the rotation",
                )


def _check_aircraft_in_maintenance(
    db: Session,
    rep: TechRep,
    live: list[Assignment],
    mros: dict[int, MroLocation],
    local_days: Callable[[Assignment], list[date]],
    found: "_Findings",
) -> None:
    """Where the Heavy Maintenance Schedule has events for an aircraft type at an MRO,
    assignments for that type should fall inside one: once the last aircraft returns to
    service there is nothing to support."""
    typed = [a for a in live if a.aircraft_type_id is not None]
    if not typed:
        return
    demand_types = dict(
        db.execute(
            select(MroDemand.id, MroDemand.demand_type).where(
                MroDemand.id.in_({a.demand_id for a in typed if a.demand_id})
            )
        ).all()
    )
    events: dict[tuple[int, int], list[MaintenanceEvent]] = defaultdict(list)
    for ev in db.scalars(
        select(MaintenanceEvent).where(
            MaintenanceEvent.status != "cancelled",
            MaintenanceEvent.mro_id.in_({a.mro_id for a in typed}),
        )
    ):
        events[ev.mro_id, ev.aircraft_type_id].append(ev)
    for a in typed:
        here = events.get((a.mro_id, a.aircraft_type_id))
        if not here or demand_types.get(a.demand_id) in UNSCHEDULED_DEMANDS:
            continue
        outside = [
            d
            for d in local_days(a)
            if not any(ev.induction_date <= d <= ev.rts_date for ev in here)
        ]
        if not outside:
            continue
        before = [ev.rts_date for ev in here if ev.rts_date < outside[0]]
        last = f"; the last one returned to service on {max(before)}" if before else ""
        found.add(
            "no_aircraft",
            "warning",
            f"{rep.name}: assignment {a.id} at {mros[a.mro_id].facility_name} from "
            f"{outside[0]} has no aircraft of its type in maintenance there{last}",
            a,
        )


def _check_seniority(
    db: Session,
    rep: TechRep,
    live: list[Assignment],
    rules: CbaRules | None,
    found: _Findings,
    years: range,
) -> None:
    """Overtime by seniority (16-1.06, 21-2.09, 21-3.08) and vacation awards by seniority."""
    overtime = [
        a for a in live if a.demand_id is not None and a.overtime_type != "none"
    ]
    if overtime and rules is not None:
        rest = timedelta(hours=float(rules.min_rest_hours))
        others = list(
            db.scalars(
                select(TechRep)
                .where(TechRep.active, TechRep.id != rep.id)
                .options(selectinload(TechRep.certifications))
            )
        )
        avail = Availability(
            db, min(a.start_time for a in overtime), max(a.end_time for a in overtime)
        )
        for a in overtime:
            responses = dict(
                db.execute(
                    select(DemandResponse.rep_id, DemandResponse.response).where(
                        DemandResponse.demand_id == a.demand_id
                    )
                ).all()
            )
            on_demand = set(
                db.scalars(
                    select(Assignment.rep_id).where(
                        Assignment.demand_id == a.demand_id,
                        Assignment.status != "cancelled",
                    )
                )
            )
            day = a.start_time.date()
            free = [
                r
                for r in others
                if r.id not in on_demand
                and (
                    a.aircraft_type_id is None
                    or is_certified(r, a.aircraft_type_id, day, day)
                )
                and avail.reason(r.id, a.start_time, a.end_time, rest) is None
            ]
            if a.overtime_type == "voluntary":
                senior = [
                    r
                    for r in free
                    if responses.get(r.id) == "accepted"
                    and seniority_key(r) < seniority_key(rep)
                ]
                if senior:
                    best = min(senior, key=seniority_key)
                    found.add(
                        "seniority",
                        "warning",
                        f"{rep.name} has voluntary overtime on assignment {a.id} while more "
                        f"senior {best.name} accepted it and is available",
                        a,
                    )
            else:
                junior = [
                    r
                    for r in free
                    if responses.get(r.id) != "accepted"
                    and seniority_key(r) > seniority_key(rep)
                ]
                if junior:
                    most_junior = max(junior, key=seniority_key)
                    found.add(
                        "seniority",
                        "warning",
                        f"Mandatory overtime on assignment {a.id} goes to the most junior "
                        f"available rep ({most_junior.name}), not {rep.name}",
                        a,
                    )

    awarded = list(
        db.scalars(
            select(VacationBid).where(
                VacationBid.rep_id == rep.id,
                VacationBid.status == "awarded",
                VacationBid.year.in_(list(years)),
            )
        )
    )
    for bid in awarded:
        denied = db.execute(
            select(TechRep)
            .join(VacationBid, VacationBid.rep_id == TechRep.id)
            .where(
                VacationBid.year == bid.year,
                VacationBid.week_start == bid.week_start,
                VacationBid.status == "denied",
            )
        ).scalars()
        senior = [r for r in denied if seniority_key(r) < seniority_key(rep)]
        if senior:
            found.add(
                "seniority",
                "warning",
                f"{rep.name} was awarded the week of {bid.week_start} while more senior "
                f"{min(senior, key=seniority_key).name} was denied it",
            )


def save_alerts(
    db: Session,
    rep_id: int,
    found: list[ComplianceWarning],
    checked: set[int],
    years: set[int],
) -> None:
    """Add new findings as alerts. Acknowledge open ones that no longer apply: those on
    checked assignments, and the rep's own leave and seniority alerts for checked years."""
    current = {(w.rep_id, w.alert_type, w.assignment_id, w.message) for w in found}
    stmt = select(Alert).where(
        ~Alert.acknowledged,
        Alert.alert_type.in_(COMPLIANCE_TYPES),
        or_(Alert.rep_id == rep_id, Alert.assignment_id.in_(checked)),
    )
    existing: set[tuple[int | None, str, int | None, str]] = set()
    for al in db.scalars(stmt):
        key = (al.rep_id, al.alert_type, al.assignment_id, al.message)
        # Rep-level messages always name the year or week they are about.
        rechecked = al.assignment_id in checked or (
            al.assignment_id is None and any(str(y) in al.message for y in years)
        )
        if rechecked and key not in current:
            al.acknowledged = True
        else:
            existing.add(key)
    for w in found:
        if (w.rep_id, w.alert_type, w.assignment_id, w.message) not in existing:
            db.add(Alert(**w.model_dump()))


def record(
    db: Session, rep_id: int, start: datetime, end: datetime
) -> list[ComplianceWarning]:
    """Check the rep around [start, end), update alerts, commit, and return the findings."""
    found, checked, years = check_rep(db, rep_id, start, end)
    save_alerts(db, rep_id, found, checked, years)
    db.commit()
    return found
