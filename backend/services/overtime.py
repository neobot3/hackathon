"""Unfilled demand as overtime opportunities, with reps ranked by seniority (BR5)."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Assignment, DemandResponse, MroDemand, MroLocation, TechRep
from schemas import EligibleRep, IneligibleRep, OvertimeOpportunity
from services.compliance import Availability, is_certified
from services.scheduler import (
    NoActiveRulesError,
    _hours_by_local_date,
    _is_field_service,
    _is_pattern_work_day,
    _tz,
    active_rules,
    is_home_team,
    seniority_key,
)


def opportunities(
    db: Session, start: datetime, end: datetime, mro_id: int | None = None
) -> list[OvertimeOpportunity]:
    rules = active_rules(db, start.date())
    if rules is None:
        raise NoActiveRulesError(f"No CBA rules in effect on {start.date()}")
    rest = timedelta(hours=float(rules.min_rest_hours))
    field_rest = timedelta(
        hours=float(max(rules.min_rest_hours, rules.post_field_rest_hours))
    )

    stmt = select(MroDemand).where(
        MroDemand.status == "open",
        MroDemand.end_time > start,
        MroDemand.start_time < end,
    )
    if mro_id is not None:
        stmt = stmt.where(MroDemand.mro_id == mro_id)
    demands = list(db.scalars(stmt.order_by(MroDemand.priority, MroDemand.start_time)))
    if not demands:
        return []
    ids = [d.id for d in demands]
    on_demand: dict[int, set[int]] = defaultdict(set)
    for demand_id, rep_id in db.execute(
        select(Assignment.demand_id, Assignment.rep_id).where(
            Assignment.demand_id.in_(ids), Assignment.status != "cancelled"
        )
    ):
        on_demand[demand_id].add(rep_id)
    filled = Counter({k: len(v) for k, v in on_demand.items()})
    responses: dict[int, dict[int, str]] = defaultdict(dict)
    for r in db.scalars(
        select(DemandResponse).where(DemandResponse.demand_id.in_(ids))
    ):
        responses[r.demand_id][r.rep_id] = r.response

    reps = sorted(
        db.scalars(
            select(TechRep)
            .where(TechRep.active)
            .options(
                selectinload(TechRep.certifications),
                selectinload(TechRep.shift_pattern),
            )
        ),
        key=seniority_key,
    )
    mros = {m.id: m for m in db.scalars(select(MroLocation))}
    avail = Availability(
        db, min(d.start_time for d in demands), max(d.end_time for d in demands)
    )

    out: list[OvertimeOpportunity] = []
    for d in demands:
        still_needed = d.reps_needed - filled[d.id]
        if still_needed <= 0:
            continue
        mro = mros[d.mro_id]
        days = sorted(_hours_by_local_date(d.start_time, d.end_time, _tz(mro.timezone)))
        eligible: list[EligibleRep] = []
        ineligible: list[IneligibleRep] = []
        for rep in reps:
            if rep.id in on_demand[d.id]:
                continue
            if not is_certified(rep, d.aircraft_type_id, days[0], days[-1]):
                ineligible.append(
                    IneligibleRep(
                        rep_id=rep.id, name=rep.name, reason="no valid certification"
                    )
                )
                continue
            field = _is_field_service(rep, mro)
            why = avail.reason(
                rep.id, d.start_time, d.end_time, field_rest if field else rest
            )
            if why:
                ineligible.append(
                    IneligibleRep(rep_id=rep.id, name=rep.name, reason=why)
                )
                continue
            work_days = [_is_pattern_work_day(rep, day) for day in days]
            eligible.append(
                EligibleRep(
                    rep_id=rep.id,
                    name=rep.name,
                    seniority_rank=rep.seniority_rank,
                    response=responses[d.id].get(rep.id),
                    field_service=field,
                    home_team=is_home_team(rep, mro),
                    pattern_day_off=None if None in work_days else not all(work_days),
                )
            )
        # The team covering the MRO is asked first; seniority decides within each group.
        eligible.sort(key=lambda e: not e.home_team)
        out.append(
            OvertimeOpportunity(
                demand_id=d.id,
                mro_id=d.mro_id,
                aircraft_type_id=d.aircraft_type_id,
                demand_type=d.demand_type,
                start_time=d.start_time,
                end_time=d.end_time,
                priority=d.priority,
                reps_needed=d.reps_needed,
                still_needed=still_needed,
                eligible=eligible,
                ineligible=ineligible,
            )
        )
    return out
