"""Leave day counting shared by compliance checks, balances, and the vacation award."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import LeaveBalance, MroLocation, RepUnavailability, TechRep
from services.dates import week_start
from services.scheduler import _hours_by_local_date, _is_pattern_work_day, home_tz


def leave_dates(entry: RepUnavailability, tz: tzinfo) -> set[date]:
    return set(_hours_by_local_date(entry.start_time, entry.end_time, tz))


def is_work_day(rep: TechRep, day: date) -> bool:
    """A shift pattern work day, or Monday to Friday for reps without a pattern."""
    pattern_day = _is_pattern_work_day(rep, day)
    return day.weekday() < 5 if pattern_day is None else pattern_day


def work_days(
    rep: TechRep, entries: Iterable[RepUnavailability], tz: tzinfo, year: int
) -> list[date]:
    """Sorted work days in `year` covered by the entries; leave is charged per work day."""
    days = {d for e in entries for d in leave_dates(e, tz) if d.year == year}
    return sorted(d for d in days if is_work_day(rep, d))


def year_bounds(year: int) -> tuple[datetime, datetime]:
    # A day of padding catches entries stored in UTC that start on the local 1 January.
    return (
        datetime.combine(date(year, 1, 1), time.min, UTC) - timedelta(days=1),
        datetime.combine(date(year + 1, 1, 1), time.min, UTC) + timedelta(days=1),
    )


def approved_leave(
    db: Session, rep_id: int, reason: str, year: int
) -> list[RepUnavailability]:
    lo, hi = year_bounds(year)
    stmt = select(RepUnavailability).where(
        RepUnavailability.rep_id == rep_id,
        RepUnavailability.reason == reason,
        RepUnavailability.status == "approved",
        RepUnavailability.end_time > lo,
        RepUnavailability.start_time < hi,
    )
    return list(db.scalars(stmt))


def biddable_days(db: Session, rep_id: int, year: int) -> float | None:
    """Vacation plus stat entitlement: stat holidays are given up front and bid with
    vacation. None when neither balance is on file."""
    balances = [db.get(LeaveBalance, (rep_id, year, t)) for t in ("vacation", "stat")]
    if all(b is None for b in balances):
        return None
    return sum(float(b.entitled_days) for b in balances if b is not None)


def recount(db: Session, rep_id: int, years: Iterable[int]) -> None:
    """Set used_days on existing vacation, stat, and sick balances from approved leave.
    Vacation leave is charged to the vacation balance first, then to stat."""
    rep = db.get(TechRep, rep_id, options=[selectinload(TechRep.shift_pattern)])
    if rep is None:
        return
    tz = home_tz(rep, db.scalars(select(MroLocation)))
    for year in years:
        sick = db.get(LeaveBalance, (rep_id, year, "sick"))
        if sick is not None:
            entries = approved_leave(db, rep_id, "sick", year)
            sick.used_days = Decimal(len(work_days(rep, entries, tz, year)))
        vacation = db.get(LeaveBalance, (rep_id, year, "vacation"))
        stat = db.get(LeaveBalance, (rep_id, year, "stat"))
        if vacation is None and stat is None:
            continue
        entries = approved_leave(db, rep_id, "vacation", year)
        taken = Decimal(len(work_days(rep, entries, tz, year)))
        if stat is None:
            vacation.used_days = taken
        elif vacation is None:
            stat.used_days = taken
        else:
            vacation.used_days = min(taken, vacation.entitled_days)
            stat.used_days = taken - vacation.used_days


def cancel_leave(db: Session, unavailability_id: int | None) -> None:
    """Cancel the leave row behind a withdrawn award or rejected training, and recount."""
    entry = db.get(RepUnavailability, unavailability_id) if unavailability_id else None
    if entry is not None and entry.status != "cancelled":
        entry.status = "cancelled"
        db.flush()
        recount(db, entry.rep_id, range(entry.start_time.year, entry.end_time.year + 1))


def vacation_weeks(db: Session, first: date, last: date) -> dict[date, set[int]]:
    """Reps with approved vacation on any day of each Monday-start week in [first, last]."""
    mros = list(db.scalars(select(MroLocation)))
    lo = datetime.combine(week_start(first), time.min, UTC) - timedelta(days=1)
    hi = datetime.combine(
        week_start(last) + timedelta(days=7), time.min, UTC
    ) + timedelta(days=1)
    rows = db.execute(
        select(RepUnavailability, TechRep)
        .join(TechRep, TechRep.id == RepUnavailability.rep_id)
        .where(
            RepUnavailability.reason == "vacation",
            RepUnavailability.status == "approved",
            RepUnavailability.end_time > lo,
            RepUnavailability.start_time < hi,
        )
    ).all()
    weeks: dict[date, set[int]] = defaultdict(set)
    for entry, rep in rows:
        for day in leave_dates(entry, home_tz(rep, mros)):
            monday = week_start(day)
            if week_start(first) <= monday <= week_start(last):
                weeks[monday].add(rep.id)
    return weeks
