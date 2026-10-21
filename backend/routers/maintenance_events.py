from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import AircraftType, MaintenanceEvent, MroLocation
from schemas import (
    CsvImportResult,
    EventStaffingOptions,
    MaintenanceEventCreate,
    MaintenanceEventRead,
    MaintenanceEventStatus,
    MaintenanceEventType,
    MaintenanceEventUpdate,
    MaintenanceEventWithDemands,
)
from services import maintenance
from services.csv_import import CSV_BODY, csv_rows, raise_row_errors, validation_message
from services.scheduler import NoActiveRulesError

router = APIRouter(prefix="/maintenance-events", tags=["maintenance events"])

UNKNOWN_IDS = "Unknown MRO location or aircraft type ID"


def _new_event(payload: MaintenanceEventCreate) -> MaintenanceEvent:
    event = MaintenanceEvent(**payload.model_dump())
    if event.reps_required is None:
        event.reps_required = maintenance.recommended_reps(event.event_type)
    return event


def _with_demands(
    db: DbSession, event: MaintenanceEvent
) -> MaintenanceEventWithDemands:
    return MaintenanceEventWithDemands.model_validate(event).model_copy(
        update={"demand_ids": maintenance.demand_ids(db, event.id)}
    )


@router.get("", response_model=list[MaintenanceEventRead])
def list_events(
    db: DbSession,
    mro_id: int | None = None,
    aircraft_type_id: int | None = None,
    event_type: MaintenanceEventType | None = None,
    status_filter: Annotated[
        MaintenanceEventStatus | None, Query(alias="status")
    ] = None,
    start: date | None = None,
    end: date | None = None,
) -> list[MaintenanceEvent]:
    """Filter by MRO, aircraft type, event type, status, and an overlapping [start, end]."""
    stmt = select(MaintenanceEvent).order_by(MaintenanceEvent.induction_date)
    if mro_id is not None:
        stmt = stmt.where(MaintenanceEvent.mro_id == mro_id)
    if aircraft_type_id is not None:
        stmt = stmt.where(MaintenanceEvent.aircraft_type_id == aircraft_type_id)
    if event_type is not None:
        stmt = stmt.where(MaintenanceEvent.event_type == event_type)
    if status_filter is not None:
        stmt = stmt.where(MaintenanceEvent.status == status_filter)
    if start is not None:
        stmt = stmt.where(MaintenanceEvent.rts_date >= start)
    if end is not None:
        stmt = stmt.where(MaintenanceEvent.induction_date <= end)
    return list(db.scalars(stmt))


@router.get("/{event_id}", response_model=MaintenanceEventRead)
def get_event(event_id: int, db: DbSession) -> MaintenanceEvent:
    event = db.get(MaintenanceEvent, event_id)
    if event is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Maintenance event not found"
        )
    return event


@router.post(
    "", response_model=MaintenanceEventWithDemands, status_code=status.HTTP_201_CREATED
)
def create_event(
    payload: MaintenanceEventCreate, db: DbSession
) -> MaintenanceEventWithDemands:
    """Add an event and one demand per support shift. reps_required defaults to the
    recommended staffing for the event type."""
    event = _new_event(payload)
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=UNKNOWN_IDS) from None
    maintenance.sync_demands(db, event)
    db.commit()
    db.refresh(event)
    return _with_demands(db, event)


@router.post(
    "/import",
    response_model=CsvImportResult,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=CSV_BODY,
)
def import_events(
    rows: Annotated[list[tuple[int, dict[str, str]]], Depends(csv_rows)], db: DbSession
) -> CsvImportResult:
    """Import Heavy Maintenance Schedule rows from a text/csv body. All rows or none.

    Columns: tail_number, event_type, induction_date, rts_date, aircraft_type (model
    name) or aircraft_type_id, mro (airport code or facility name) or mro_id, and the
    optional reps_required and notes.
    """
    types = {t.model_name.lower(): t.id for t in db.scalars(select(AircraftType))}
    mros: dict[str, int] = {}
    for m in db.scalars(select(MroLocation)):
        mros[m.facility_name.lower()] = m.id
        if m.airport_code:
            mros[m.airport_code.lower()] = m.id

    events: list[MaintenanceEvent] = []
    errors: list[tuple[int, str]] = []
    for line, row in rows:
        aircraft_type_id = row.get("aircraft_type_id") or types.get(
            row.get("aircraft_type", "").lower()
        )
        mro_id = row.get("mro_id") or mros.get(row.get("mro", "").lower())
        if not aircraft_type_id:
            errors.append((line, f"Unknown aircraft type {row.get('aircraft_type')!r}"))
            continue
        if not mro_id:
            errors.append((line, f"Unknown MRO {row.get('mro')!r}"))
            continue
        fields = {
            "aircraft_type_id": aircraft_type_id,
            "mro_id": mro_id,
            "tail_number": row.get("tail_number"),
            "event_type": row.get("event_type"),
            "induction_date": row.get("induction_date"),
            "rts_date": row.get("rts_date"),
            "notes": row.get("notes") or None,
        }
        if row.get("reps_required"):
            fields["reps_required"] = row["reps_required"]
        try:
            payload = MaintenanceEventCreate.model_validate(fields)
        except ValidationError as exc:
            errors.append((line, validation_message(exc)))
            continue
        events.append(_new_event(payload))
    raise_row_errors(errors)

    db.add_all(events)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=UNKNOWN_IDS) from None
    for event in events:
        maintenance.sync_demands(db, event)
    db.commit()
    return CsvImportResult(created=len(events), ids=[e.id for e in events])


@router.patch("/{event_id}", response_model=MaintenanceEventWithDemands)
def update_event(
    event_id: int, payload: MaintenanceEventUpdate, db: DbSession
) -> MaintenanceEventWithDemands:
    """New induction or RTS dates, staffing, or status update the event's demands.
    Assignments on shifts the event no longer needs are flagged in alerts."""
    event = get_event(event_id, db)
    before = (event.induction_date, event.rts_date, event.reps_required, event.status)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    if event.rts_date < event.induction_date:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="rts_date must be on or after induction_date",
        )
    if (
        event.induction_date,
        event.rts_date,
        event.reps_required,
        event.status,
    ) != before:
        changed = []
        if event.induction_date != before[0]:
            changed.append(f"induction moved to {event.induction_date}")
        if event.rts_date != before[1]:
            changed.append(f"RTS moved to {event.rts_date}")
        if event.status != before[3]:
            changed.append(f"event {event.status}")
        maintenance.sync_demands(db, event, ", ".join(changed) or None)
    db.commit()
    return _with_demands(db, event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: DbSession) -> None:
    """Cancels the event's demands, flagging their assignments, then deletes it."""
    event = get_event(event_id, db)
    event.status = "cancelled"
    maintenance.sync_demands(db, event, "event deleted")
    db.delete(event)
    db.commit()


@router.get("/{event_id}/staffing-options", response_model=EventStaffingOptions)
def event_staffing_options(event_id: int, db: DbSession) -> EventStaffingOptions:
    """For unplanned events: per open shift, the available qualified reps by seniority,
    and reps on lower-priority work at the same time who could be reassigned."""
    try:
        return maintenance.staffing_options(db, get_event(event_id, db))
    except NoActiveRulesError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None
