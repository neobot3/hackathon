from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import Assignment
from schemas import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentStatus,
    AssignmentUpdate,
    AssignmentWithWarnings,
)
from services import compliance

router = APIRouter(prefix="/assignments", tags=["assignments"])

# Cancelled and completed are final; reopening could double-book a rep.
TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"confirmed", "cancelled"},
    "confirmed": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


@router.get("", response_model=list[AssignmentRead])
def list_assignments(
    db: DbSession,
    rep_id: int | None = None,
    mro_id: int | None = None,
    demand_id: int | None = None,
    status_filter: Annotated[AssignmentStatus | None, Query(alias="status")] = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Assignment]:
    """Filter by rep, MRO, demand, status, and an overlapping [start, end) window."""
    stmt = select(Assignment).order_by(Assignment.start_time)
    if rep_id is not None:
        stmt = stmt.where(Assignment.rep_id == rep_id)
    if mro_id is not None:
        stmt = stmt.where(Assignment.mro_id == mro_id)
    if demand_id is not None:
        stmt = stmt.where(Assignment.demand_id == demand_id)
    if status_filter is not None:
        stmt = stmt.where(Assignment.status == status_filter)
    if start is not None:
        stmt = stmt.where(Assignment.end_time > start)
    if end is not None:
        stmt = stmt.where(Assignment.start_time < end)
    return list(db.scalars(stmt))


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(assignment_id: int, db: DbSession) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


@router.post("", response_model=AssignmentWithWarnings, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate, db: DbSession) -> AssignmentWithWarnings:
    """Manual assignment, for overriding the solver. Saved even when it breaks a rule;
    compliance findings come back as warnings and are written to alerts."""
    assignment = Assignment(**payload.model_dump())
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Rep already has an overlapping assignment, or an ID does not exist",
        ) from None
    db.refresh(assignment)
    warnings = compliance.record(db, assignment.rep_id, assignment.start_time, assignment.end_time)
    return AssignmentWithWarnings.model_validate(assignment).model_copy(
        update={"warnings": warnings}
    )


@router.patch("/{assignment_id}", response_model=AssignmentWithWarnings)
def update_assignment(
    assignment_id: int, payload: AssignmentUpdate, db: DbSession
) -> AssignmentWithWarnings:
    """Change status, rep, or times. Rep and times are fixed once completed or cancelled."""
    assignment = get_assignment(assignment_id, db)
    changes = payload.model_dump(exclude_unset=True)
    new_status = changes.pop("status", assignment.status)
    if new_status != assignment.status and new_status not in TRANSITIONS[assignment.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot change status from {assignment.status} to {new_status}",
        )
    if changes and not TRANSITIONS[assignment.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"Cannot edit a {assignment.status} assignment"
        )
    old_rep, old_start, old_end = assignment.rep_id, assignment.start_time, assignment.end_time
    for field, value in changes.items():
        setattr(assignment, field, value)
    assignment.status = new_status
    if assignment.end_time <= assignment.start_time:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_time must be after start_time"
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Rep already has an overlapping assignment, or the rep ID does not exist",
        ) from None
    warnings = compliance.record(
        db,
        assignment.rep_id,
        min(old_start, assignment.start_time),
        max(old_end, assignment.end_time),
    )
    if old_rep != assignment.rep_id:
        compliance.record(db, old_rep, old_start, old_end)
    return AssignmentWithWarnings.model_validate(assignment).model_copy(
        update={"warnings": warnings}
    )
