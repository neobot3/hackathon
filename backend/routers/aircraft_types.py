from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import AircraftType
from schemas import AircraftTypeCreate, AircraftTypeRead

router = APIRouter(prefix="/aircraft-types", tags=["aircraft types"])


@router.get("", response_model=list[AircraftTypeRead])
def list_aircraft_types(db: DbSession) -> list[AircraftType]:
    return list(db.scalars(select(AircraftType).order_by(AircraftType.model_name)))


@router.get("/{type_id}", response_model=AircraftTypeRead)
def get_aircraft_type(type_id: int, db: DbSession) -> AircraftType:
    aircraft_type = db.get(AircraftType, type_id)
    if aircraft_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aircraft type not found")
    return aircraft_type


@router.post("", response_model=AircraftTypeRead, status_code=status.HTTP_201_CREATED)
def create_aircraft_type(payload: AircraftTypeCreate, db: DbSession) -> AircraftType:
    aircraft_type = AircraftType(**payload.model_dump())
    db.add(aircraft_type)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="An aircraft type with that model name exists"
        ) from None
    return aircraft_type
