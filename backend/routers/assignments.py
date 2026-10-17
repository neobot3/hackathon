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
    AssignmentStatusUpdate,
)

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


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate, db: DbSession) -> Assignment:
    """Manual assignment, for overriding the solver. CBA rules are not checked here."""
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
    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentRead)
def update_assignment_status(
    assignment_id: int, payload: AssignmentStatusUpdate, db: DbSession
) -> Assignment:
    assignment = get_assignment(assignment_id, db)
    if payload.status != assignment.status and payload.status not in TRANSITIONS[assignment.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot change status from {assignment.status} to {payload.status}",
        )
    assignment.status = payload.status
    db.commit()
    return assignment
