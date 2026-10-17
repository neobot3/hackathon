from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import DemandResponse, MroDemand, TechRep
from schemas import (
    DemandCreate,
    DemandRead,
    DemandResponseRead,
    DemandResponseUpsert,
    DemandStatus,
    DemandStatusUpdate,
    DemandType,
)

router = APIRouter(prefix="/demands", tags=["demands"])


@router.get("", response_model=list[DemandRead])
def list_demands(
    db: DbSession,
    mro_id: int | None = None,
    demand_type: DemandType | None = None,
    status_filter: Annotated[DemandStatus | None, Query(alias="status")] = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[MroDemand]:
    """Filter by MRO, type, status, and an overlapping [start, end) window."""
    stmt = select(MroDemand).order_by(MroDemand.priority, MroDemand.start_time)
    if mro_id is not None:
        stmt = stmt.where(MroDemand.mro_id == mro_id)
    if demand_type is not None:
        stmt = stmt.where(MroDemand.demand_type == demand_type)
    if status_filter is not None:
        stmt = stmt.where(MroDemand.status == status_filter)
    if start is not None:
        stmt = stmt.where(MroDemand.end_time > start)
    if end is not None:
        stmt = stmt.where(MroDemand.start_time < end)
    return list(db.scalars(stmt))


@router.get("/{demand_id}", response_model=DemandRead)
def get_demand(demand_id: int, db: DbSession) -> MroDemand:
    demand = db.get(MroDemand, demand_id)
    if demand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Demand not found")
    return demand


@router.post("", response_model=DemandRead, status_code=status.HTTP_201_CREATED)
def create_demand(payload: DemandCreate, db: DbSession) -> MroDemand:
    demand = MroDemand(**payload.model_dump())
    db.add(demand)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Unknown MRO location or aircraft type ID"
        ) from None
    db.refresh(demand)
    return demand


@router.patch("/{demand_id}", response_model=DemandRead)
def update_demand_status(demand_id: int, payload: DemandStatusUpdate, db: DbSession) -> MroDemand:
    demand = get_demand(demand_id, db)
    demand.status = payload.status
    db.commit()
    return demand


@router.get("/{demand_id}/responses", response_model=list[DemandResponseRead])
def list_responses(demand_id: int, db: DbSession) -> list[DemandResponse]:
    get_demand(demand_id, db)
    stmt = (
        select(DemandResponse)
        .where(DemandResponse.demand_id == demand_id)
        .order_by(DemandResponse.responded_at)
    )
    return list(db.scalars(stmt))


@router.put("/{demand_id}/responses/{rep_id}", response_model=DemandResponseRead)
def record_response(
    demand_id: int, rep_id: int, payload: DemandResponseUpsert, db: DbSession
) -> DemandResponse:
    """Record a rep accepting or declining. Any response marks the demand as solicited."""
    get_demand(demand_id, db)
    if db.get(TechRep, rep_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tech rep not found")
    response = db.get(DemandResponse, (demand_id, rep_id))
    if response is None:
        response = DemandResponse(demand_id=demand_id, rep_id=rep_id)
        db.add(response)
    response.response = payload.response
    response.responded_at = func.now()
    db.commit()
    db.refresh(response)
    return response


@router.delete("/{demand_id}/responses/{rep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_response(demand_id: int, rep_id: int, db: DbSession) -> None:
    response = db.get(DemandResponse, (demand_id, rep_id))
    if response is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Response not found")
    db.delete(response)
    db.commit()
