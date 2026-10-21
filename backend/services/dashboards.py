"""Workforce and coverage dashboard data (BR11)."""

from collections import Counter, defaultdict
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Assignment, MroDemand, MroLocation, RepUnavailability, TechRep
from schemas import CoverageWeek, WorkforceRep, WorkforceSummary
from services.dates import week_start
from services.scheduler import _tz


def workforce(
    db: Session, start: datetime, end: datetime, mro_id: int | None = None
) -> WorkforceSummary:
    """Each active rep in [start, end): assigned, on approved leave, or available.

    With mro_id, only reps based at or assigned to that MRO.
    """
    reps = list(
        db.scalars(select(TechRep).where(TechRep.active).order_by(TechRep.name))
    )
    assignments = list(
        db.scalars(
            select(Assignment).where(
                Assignment.status != "cancelled",
                Assignment.end_time > start,
                Assignment.start_time < end,
            )
        )
    )
    leave = list(
        db.scalars(
            select(RepUnavailability).where(
                RepUnavailability.status == "approved",
                RepUnavailability.end_time > start,
                RepUnavailability.start_time < end,
            )
        )
    )
    mros_by_rep: dict[int, set[int]] = defaultdict(set)
    hours: Counter[int] = Counter()
    for a in assignments:
        mros_by_rep[a.rep_id].add(a.mro_id)
        hours[a.rep_id] += (
            min(a.end_time, end) - max(a.start_time, start)
        ).total_seconds() / 3600
    reasons: dict[int, set[str]] = defaultdict(set)
    for u in leave:
        reasons[u.rep_id].add(u.reason)

    if mro_id is not None:
        mro = db.get(MroLocation, mro_id)
        local = (
            {mro.location.strip().lower(), (mro.airport_code or "").strip().lower()}
            if mro
            else set()
        )
        reps = [
            r
            for r in reps
            if mro_id in mros_by_rep[r.id] or r.home_base.strip().lower() in local
        ]

    rows = [
        WorkforceRep(
            rep_id=r.id,
            name=r.name,
            home_base=r.home_base,
            status=(
                "assigned"
                if mros_by_rep[r.id]
                else "on_leave"
                if reasons[r.id]
                else "available"
            ),
            mro_ids=sorted(mros_by_rep[r.id]),
            leave_reasons=sorted(reasons[r.id]),
            assigned_hours=round(hours[r.id], 2),
        )
        for r in reps
    ]
    counts = Counter(r.status for r in rows)
    return WorkforceSummary(
        start=start,
        end=end,
        available=counts["available"],
        assigned=counts["assigned"],
        on_leave=counts["on_leave"],
        reps=rows,
    )


def coverage(
    db: Session, start: datetime, end: datetime, mro_id: int | None = None
) -> list[CoverageWeek]:
    """Seats needed and filled per MRO per week, from demands that are not cancelled."""
    stmt = select(MroDemand).where(
        MroDemand.status != "cancelled",
        MroDemand.end_time > start,
        MroDemand.start_time < end,
    )
    if mro_id is not None:
        stmt = stmt.where(MroDemand.mro_id == mro_id)
    demands = list(db.scalars(stmt))
    filled = Counter(
        db.scalars(
            select(Assignment.demand_id).where(
                Assignment.demand_id.in_([d.id for d in demands]),
                Assignment.status != "cancelled",
            )
        )
    )
    tz = {m.id: _tz(m.timezone) for m in db.scalars(select(MroLocation))}
    weeks: dict[tuple[int, date], list[int]] = defaultdict(lambda: [0, 0, 0])
    for d in demands:
        week = weeks[d.mro_id, week_start(d.start_time.astimezone(tz[d.mro_id]).date())]
        week[0] += 1
        week[1] += d.reps_needed
        week[2] += min(filled[d.id], d.reps_needed)
    return [
        CoverageWeek(
            mro_id=m,
            week_start=w,
            shifts=shifts,
            seats_needed=needed,
            seats_filled=done,
            gap=needed - done,
        )
        for (m, w), (shifts, needed, done) in sorted(
            weeks.items(), key=lambda kv: (kv[0][1], kv[0][0])
        )
    ]
