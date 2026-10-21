"""Vacation bid awards by seniority and weekly vacation capacity (BR4)."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import MroLocation, RepUnavailability, TechRep, VacationBid
from schemas import VacationAwardDenied, VacationAwardResult, VacationCapacityWeek
from services import leave
from services.scheduler import active_rules, home_tz, seniority_key


def _cap(db: Session, week: date) -> int | None:
    rules = active_rules(db, week)
    return None if rules is None else rules.max_reps_off_per_week


def award(db: Session, year: int) -> VacationAwardResult:
    """Award submitted bids for `year`: each rep in seniority order, best preference first.

    A week is awarded while it is under the weekly cap and the rep has enough vacation
    and stat balance left. Each award becomes an approved vacation leave row for that week.
    """
    bids = list(
        db.scalars(
            select(VacationBid)
            .where(VacationBid.year == year, VacationBid.status == "submitted")
            .order_by(VacationBid.preference_rank)
        )
    )
    reps = {
        r.id: r
        for r in db.scalars(
            select(TechRep)
            .where(TechRep.id.in_({b.rep_id for b in bids}))
            .options(selectinload(TechRep.shift_pattern))
        )
    }
    mros = list(db.scalars(select(MroLocation)))
    first, last = (
        date(year, 1, 1) - timedelta(days=7),
        date(year, 12, 31) + timedelta(days=7),
    )
    off = leave.vacation_weeks(db, first, last)
    caps: dict[date, int | None] = {}
    result = VacationAwardResult(year=year, awarded=[], denied=[])

    for rep in sorted(reps.values(), key=seniority_key):
        tz = home_tz(rep, mros)
        entitled = leave.biddable_days(db, rep.id, year)
        remaining = 0.0
        if entitled is not None:
            taken = leave.work_days(
                rep, leave.approved_leave(db, rep.id, "vacation", year), tz, year
            )
            remaining = entitled - len(taken)
        for bid in (b for b in bids if b.rep_id == rep.id):
            week = bid.week_start
            if week not in caps:
                caps[week] = _cap(db, week)
            start = datetime.combine(week, time.min, tz)
            end = datetime.combine(week + timedelta(days=7), time.min, tz)
            days = len(
                [
                    d
                    for d in (week + timedelta(days=i) for i in range(7))
                    if d.year == year and leave.is_work_day(rep, d)
                ]
            )
            reason = None
            if rep.id in off[week]:
                reason = "Already on vacation that week"
            elif caps[week] is None:
                reason = f"No CBA rules in effect on {week}"
            elif len(off[week]) >= caps[week]:
                reason = f"Week is full ({len(off[week])} of {caps[week]} reps off)"
            elif entitled is None:
                reason = f"No vacation or stat balance on file for {year}"
            elif days > remaining:
                reason = f"Needs {days} days; {remaining:g} left"
            if reason:
                bid.status = "denied"
                result.denied.append(
                    VacationAwardDenied(
                        bid_id=bid.id, rep_id=rep.id, week_start=week, reason=reason
                    )
                )
                continue
            entry = RepUnavailability(
                rep_id=rep.id,
                reason="vacation",
                start_time=start.astimezone(UTC),
                end_time=end.astimezone(UTC),
                status="approved",
                notes=f"Vacation bid {bid.id}",
            )
            db.add(entry)
            db.flush()
            bid.status = "awarded"
            bid.unavailability_id = entry.id
            off[week].add(rep.id)
            remaining -= days
            result.awarded.append(bid.id)
        leave.recount(db, rep.id, [year])
    db.commit()
    return result


def capacity(db: Session, year: int) -> list[VacationCapacityWeek]:
    """Every Monday-start week that begins in `year`, with reps on approved vacation."""
    monday = date(year, 1, 1) + timedelta(days=(7 - date(year, 1, 1).weekday()) % 7)
    off = leave.vacation_weeks(db, monday, date(year, 12, 31))
    weeks: list[VacationCapacityWeek] = []
    while monday.year == year:
        cap = _cap(db, monday) or 0
        reps_off = sorted(off.get(monday, ()))
        weeks.append(
            VacationCapacityWeek(
                week_start=monday,
                cap=cap,
                reps_off=len(reps_off),
                remaining=max(0, cap - len(reps_off)),
                rep_ids=reps_off,
            )
        )
        monday += timedelta(days=7)
    return weeks
