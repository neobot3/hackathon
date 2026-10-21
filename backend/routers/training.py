from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import RepTraining, TrainingType
from schemas import (
    RepTrainingCreate,
    RepTrainingRead,
    RepTrainingUpdate,
    TrainingApproval,
    TrainingDue,
    TrainingRejection,
    TrainingStatus,
    TrainingTypeCreate,
    TrainingTypeRead,
    TrainingTypeUpdate,
)
from services import compliance, leave, training
from services.dates import add_months

router = APIRouter(prefix="/training", tags=["training"])

TYPE_CONFLICT = (
    "A training type with that name exists, or the aircraft type ID does not exist"
)


@router.get("/types", response_model=list[TrainingTypeRead])
def list_training_types(db: DbSession) -> list[TrainingType]:
    return list(db.scalars(select(TrainingType).order_by(TrainingType.name)))


@router.get("/types/{type_id}", response_model=TrainingTypeRead)
def get_training_type(type_id: int, db: DbSession) -> TrainingType:
    training_type = db.get(TrainingType, type_id)
    if training_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Training type not found")
    return training_type


@router.post(
    "/types", response_model=TrainingTypeRead, status_code=status.HTTP_201_CREATED
)
def create_training_type(payload: TrainingTypeCreate, db: DbSession) -> TrainingType:
    training_type = TrainingType(**payload.model_dump())
    db.add(training_type)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=TYPE_CONFLICT) from None
    db.refresh(training_type)
    return training_type


@router.patch("/types/{type_id}", response_model=TrainingTypeRead)
def update_training_type(
    type_id: int, payload: TrainingTypeUpdate, db: DbSession
) -> TrainingType:
    training_type = get_training_type(type_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(training_type, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=TYPE_CONFLICT) from None
    return training_type


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training_type(type_id: int, db: DbSession) -> None:
    db.delete(get_training_type(type_id, db))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Training records still use this type"
        ) from None


@router.get("/records", response_model=list[RepTrainingRead])
def list_training_records(
    db: DbSession,
    rep_id: int | None = None,
    training_type_id: int | None = None,
    status_filter: Annotated[TrainingStatus | None, Query(alias="status")] = None,
) -> list[RepTraining]:
    stmt = select(RepTraining).order_by(RepTraining.rep_id, RepTraining.id)
    if rep_id is not None:
        stmt = stmt.where(RepTraining.rep_id == rep_id)
    if training_type_id is not None:
        stmt = stmt.where(RepTraining.training_type_id == training_type_id)
    if status_filter is not None:
        stmt = stmt.where(RepTraining.status == status_filter)
    return list(db.scalars(stmt))


@router.get("/records/{record_id}", response_model=RepTrainingRead)
def get_training_record(record_id: int, db: DbSession) -> RepTraining:
    record = db.get(RepTraining, record_id)
    if record is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Training record not found"
        )
    return record


def _default_expiry(record: RepTraining, db: DbSession) -> None:
    training_type = db.get(TrainingType, record.training_type_id)
    if (
        record.expires_on is None
        and record.completed_on is not None
        and training_type is not None
        and training_type.recurrence_months
    ):
        record.expires_on = add_months(
            record.completed_on, training_type.recurrence_months
        )


@router.post(
    "/records", response_model=RepTrainingRead, status_code=status.HTTP_201_CREATED
)
def create_training_record(payload: RepTrainingCreate, db: DbSession) -> RepTraining:
    """Record completed training, or submit training dates for the scheduler to approve.

    A record without scheduled dates is history and is stored as approved.
    """
    record = RepTraining(**payload.model_dump())
    record.status = "submitted" if payload.scheduled_start else "approved"
    _default_expiry(record, db)
    training.certify(db, record)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Unknown tech rep or training type ID"
        ) from None
    db.refresh(record)
    return record


@router.patch("/records/{record_id}", response_model=RepTrainingRead)
def update_training_record(
    record_id: int, payload: RepTrainingUpdate, db: DbSession
) -> RepTraining:
    """New scheduled dates on approved training send it back for approval."""
    record = get_training_record(record_id, db)
    old_dates = (record.scheduled_start, record.scheduled_end)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    if (
        "completed_on" in payload.model_fields_set
        and "expires_on" not in payload.model_fields_set
    ):
        record.expires_on = None
        _default_expiry(record, db)
        training.certify(db, record)
    if (
        record.status == "approved"
        and (record.scheduled_start, record.scheduled_end) != old_dates
    ):
        leave.cancel_leave(db, record.unavailability_id)
        record.unavailability_id = None
        record.status = "submitted" if record.scheduled_start else "approved"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scheduled dates must both be set with end after start, "
            "and expires_on must not be before completed_on",
        ) from None
    return record


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training_record(record_id: int, db: DbSession) -> None:
    """Deleting approved training also cancels its leave."""
    record = get_training_record(record_id, db)
    leave.cancel_leave(db, record.unavailability_id)
    db.delete(record)
    db.commit()


@router.post("/records/{record_id}/approve", response_model=TrainingApproval)
def approve_training(record_id: int, db: DbSession) -> TrainingApproval:
    """Approve submitted dates. The rep is blocked for the session, proposed assignments
    in the way are cancelled, and other clashes come back as warnings and alerts."""
    record = get_training_record(record_id, db)
    if record.scheduled_start is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Training has no scheduled dates",
        )
    cancelled = training.approve(db, record)
    db.commit()
    warnings = compliance.record(
        db, record.rep_id, record.scheduled_start, record.scheduled_end
    )
    return TrainingApproval.model_validate(record).model_copy(
        update={"cancelled_assignment_ids": cancelled, "warnings": warnings}
    )


@router.post("/records/{record_id}/reject", response_model=RepTrainingRead)
def reject_training(
    record_id: int, db: DbSession, payload: TrainingRejection | None = None
) -> RepTraining:
    """Reject submitted dates and send them back to the training department with an
    optional note. Rejecting approved training cancels its leave."""
    record = get_training_record(record_id, db)
    if record.scheduled_start is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Training has no scheduled dates",
        )
    leave.cancel_leave(db, record.unavailability_id)
    record.unavailability_id = None
    record.status = "rejected"
    if payload is not None and payload.note:
        record.notes = " ".join(
            filter(None, [record.notes, f"Rejected: {payload.note}"])
        )[-500:]
    db.commit()
    return record


@router.get("/due", response_model=list[TrainingDue])
def list_training_due(
    db: DbSession, days: Annotated[int, Query(ge=0, le=3650)] = 60
) -> list[TrainingDue]:
    """Active reps whose training expires within `days`, has expired, or (mandatory
    training only) was never completed. Soonest expiry first."""
    return training.due(db, days)
