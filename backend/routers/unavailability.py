from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import RepUnavailability
from schemas import (
    UnavailabilityCreate,
    UnavailabilityRead,
    UnavailabilityStatus,
    UnavailabilityStatusUpdate,
)

router = APIRouter(prefix="/unavailability", tags=["unavailability"])


@router.get("", response_model=list[UnavailabilityRead])
def list_unavailability(
    db: DbSession,
    rep_id: int | None = None,
    status_filter: Annotated[UnavailabilityStatus | None, Query(alias="status")] = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[RepUnavailability]:
    """Filter by rep, status, and an overlapping [start, end) window."""
    stmt = select(RepUnavailability).order_by(RepUnavailability.start_time)
    if rep_id is not None:
        stmt = stmt.where(RepUnavailability.rep_id == rep_id)
    if status_filter is not None:
        stmt = stmt.where(RepUnavailability.status == status_filter)
    if start is not None:
        stmt = stmt.where(RepUnavailability.end_time > start)
    if end is not None:
        stmt = stmt.where(RepUnavailability.start_time < end)
    return list(db.scalars(stmt))


@router.get("/{entry_id}", response_model=UnavailabilityRead)
def get_unavailability(entry_id: int, db: DbSession) -> RepUnavailability:
    entry = db.get(RepUnavailability, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unavailability entry not found")
    return entry


@router.post("", response_model=UnavailabilityRead, status_code=status.HTTP_201_CREATED)
def create_unavailability(payload: UnavailabilityCreate, db: DbSession) -> RepUnavailability:
    entry = RepUnavailability(**payload.model_dump())
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Unknown tech rep ID") from None
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=UnavailabilityRead)
def update_unavailability_status(
    entry_id: int, payload: UnavailabilityStatusUpdate, db: DbSession
) -> RepUnavailability:
    entry = get_unavailability(entry_id, db)
    entry.status = payload.status
    db.commit()
    return entry
