"""Staffing for Heavy Maintenance Schedule and unplanned events (BR7, BR8)."""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Alert, Assignment, MaintenanceEvent, MroDemand, MroLocation, TechRep
from schemas import EventStaffingOption, EventStaffingOptions, Reassignment
from services import overtime
from services.compliance import Availability, is_certified
from services.scheduler import _tz, active_rules, seniority_key

# Each support day is one local day shift, ending at end of shift on the RTS date.
SHIFT_START = time(7, 0)
SHIFT_HOURS = 10
# Recommended staffing when an event is entered without reps_required.
RECOMMENDED_REPS = {"heavy_check": 2}
# Demand priority by event type, 1 = most urgent.
EVENT_PRIORITY = {
    "aog": 1,
    "hard_landing": 2,
    "hail_damage": 2,
    "rts": 2,
    "induction": 3,
    "heavy_check": 3,
    "lease_return": 3,
    "mro_support": 4,
}


def recommended_reps(event_type: str) -> int:
    return RECOMMENDED_REPS.get(event_type, 1)


def support_days(event: MaintenanceEvent) -> list[date]:
    if event.event_type == "induction":
        return [event.induction_date]
    if event.event_type == "rts":
        return [event.rts_date]
    n = (event.rts_date - event.induction_date).days + 1
    return [event.induction_date + timedelta(days=i) for i in range(n)]


def _flag(db: Session, event: MaintenanceEvent, a: Assignment, message: str) -> None:
    db.add(
        Alert(
            alert_type="date_conflict",
            severity="warning",
            mro_id=a.mro_id,
            rep_id=a.rep_id,
            demand_id=a.demand_id,
            assignment_id=a.id,
            message=f"{event.tail_number} {event.event_type}: {message}"[:500],
        )
    )


def sync_demands(
    db: Session, event: MaintenanceEvent, changed: str | None = None
) -> None:
    """Make the event's demands match its support days and staffing.

    Demands for days the event no longer covers are cancelled and their live
    assignments flagged. `changed` describes an edit, for the alert text.
    """
    if event.status == "completed":
        return
    tz = _tz(db.get(MroLocation, event.mro_id).timezone)
    wanted = set() if event.status == "cancelled" else set(support_days(event))
    demands = db.scalars(
        select(MroDemand).where(
            MroDemand.maintenance_event_id == event.id, MroDemand.status != "cancelled"
        )
    )
    by_day = {d.start_time.astimezone(tz).date(): d for d in demands}
    for day, demand in by_day.items():
        if day in wanted:
            if demand.status == "open":
                demand.reps_needed = event.reps_required
                demand.mro_id = event.mro_id
                demand.aircraft_type_id = event.aircraft_type_id
            continue
        demand.status = "cancelled"
        for a in db.scalars(
            select(Assignment).where(
                Assignment.demand_id == demand.id, Assignment.status != "cancelled"
            )
        ):
            _flag(
                db,
                event,
                a,
                f"{changed or 'event changed'}; assignment {a.id} on {day} "
                "is outside the new dates",
            )
    new_days = sorted(wanted - set(by_day))
    for day in new_days:
        start = datetime.combine(day, SHIFT_START, tz)
        db.add(
            MroDemand(
                mro_id=event.mro_id,
                aircraft_type_id=event.aircraft_type_id,
                demand_type=event.event_type,
                start_time=start,
                end_time=start + timedelta(hours=SHIFT_HOURS),
                reps_needed=event.reps_required,
                priority=EVENT_PRIORITY[event.event_type],
                notes=f"{event.tail_number} {event.event_type}",
                maintenance_event_id=event.id,
            )
        )
    if changed and new_days:
        db.add(
            Alert(
                alert_type="date_conflict",
                severity="warning",
                mro_id=event.mro_id,
                message=f"{event.tail_number} {event.event_type}: {changed}; "
                f"{len(new_days)} new shift(s) from {new_days[0]} need staffing",
            )
        )
    db.flush()


def demand_ids(db: Session, event_id: int) -> list[int]:
    return list(
        db.scalars(
            select(MroDemand.id)
            .where(
                MroDemand.maintenance_event_id == event_id,
                MroDemand.status != "cancelled",
            )
            .order_by(MroDemand.start_time)
        )
    )


def staffing_options(db: Session, event: MaintenanceEvent) -> EventStaffingOptions:
    """For each open shift: available qualified reps, and reps on lower-priority work at
    the same time who could be moved."""
    demands = list(
        db.scalars(
            select(MroDemand)
            .where(
                MroDemand.maintenance_event_id == event.id, MroDemand.status == "open"
            )
            .order_by(MroDemand.start_time)
        )
    )
    if not demands:
        return EventStaffingOptions(event_id=event.id, demands=[])
    start = min(d.start_time for d in demands)
    end = max(d.end_time for d in demands)
    ours = {d.id for d in demands}
    found = [
        o
        for o in overtime.opportunities(db, start, end, event.mro_id)
        if o.demand_id in ours
    ]
    rules = active_rules(db, start.date())
    rest = timedelta(hours=float(rules.min_rest_hours))
    avail = Availability(db, start, end)
    reps = {
        r.id: r
        for r in db.scalars(
            select(TechRep)
            .where(TechRep.active)
            .options(selectinload(TechRep.certifications))
        )
    }
    live = {
        a.id: a
        for a in db.scalars(
            select(Assignment).where(
                Assignment.status.in_(("proposed", "confirmed")),
                Assignment.end_time > start - rest,
                Assignment.start_time < end + rest,
            )
        )
    }
    priorities = dict(
        db.execute(
            select(MroDemand.id, MroDemand.priority).where(
                MroDemand.id.in_({a.demand_id for a in live.values() if a.demand_id})
            )
        ).all()
    )

    options: list[EventStaffingOption] = []
    for o in found:
        moves: list[Reassignment] = []
        busy_reps = {
            i.rep_id for i in o.ineligible if i.reason.startswith("already booked")
        }
        for rep_id in sorted(busy_reps, key=lambda r: seniority_key(reps[r])):
            clashes = [
                a
                for a in live.values()
                if a.rep_id == rep_id
                and a.start_time < o.end_time + rest
                and o.start_time < a.end_time + rest
            ]
            less_urgent = all(
                a.demand_id is None or priorities.get(a.demand_id, 5) > o.priority
                for a in clashes
            )
            frees_rep = (
                avail.reason(
                    rep_id,
                    o.start_time,
                    o.end_time,
                    rest,
                    ignore=[a.id for a in clashes],
                )
                is None
            )
            if clashes and less_urgent and frees_rep:
                rep = reps[rep_id]
                day = o.start_time.date()
                if is_certified(rep, o.aircraft_type_id, day, day):
                    a = clashes[0]
                    moves.append(
                        Reassignment(
                            rep_id=rep.id,
                            name=rep.name,
                            seniority_rank=rep.seniority_rank,
                            assignment_id=a.id,
                            from_mro_id=a.mro_id,
                            from_demand_id=a.demand_id,
                            from_priority=priorities.get(a.demand_id),
                        )
                    )
        options.append(EventStaffingOption(**o.model_dump(), reassignments=moves))
    return EventStaffingOptions(event_id=event.id, demands=options)
