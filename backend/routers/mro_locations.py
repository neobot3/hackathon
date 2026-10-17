from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from database import DbSession
from models import MroLocation, TravelTime
from schemas import (
    MroLocationCreate,
    MroLocationRead,
    MroLocationUpdate,
    TravelTimeRead,
    TravelTimeUpsert,
)

router = APIRouter(prefix="/mro-locations", tags=["mro locations"])


@router.get("", response_model=list[MroLocationRead])
def list_mro_locations(db: DbSession) -> list[MroLocation]:
    return list(db.scalars(select(MroLocation).order_by(MroLocation.facility_name)))


@router.get("/{mro_id}", response_model=MroLocationRead)
def get_mro_location(mro_id: int, db: DbSession) -> MroLocation:
    mro = db.get(MroLocation, mro_id)
    if mro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="MRO location not found")
    return mro


@router.post("", response_model=MroLocationRead, status_code=status.HTTP_201_CREATED)
def create_mro_location(payload: MroLocationCreate, db: DbSession) -> MroLocation:
    mro = MroLocation(**payload.model_dump())
    db.add(mro)
    db.commit()
    return mro


@router.patch("/{mro_id}", response_model=MroLocationRead)
def update_mro_location(mro_id: int, payload: MroLocationUpdate, db: DbSession) -> MroLocation:
    mro = get_mro_location(mro_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(mro, field, value)
    db.commit()
    return mro


@router.get("/{mro_id}/travel-times", response_model=list[TravelTimeRead])
def list_travel_times(mro_id: int, db: DbSession) -> list[TravelTime]:
    get_mro_location(mro_id, db)
    stmt = select(TravelTime).where(TravelTime.mro_id == mro_id).order_by(TravelTime.home_base)
    return list(db.scalars(stmt))


@router.put("/{mro_id}/travel-times/{home_base}", response_model=TravelTimeRead)
def upsert_travel_time(
    mro_id: int, home_base: str, payload: TravelTimeUpsert, db: DbSession
) -> TravelTime:
    """Set one-way travel from a home base (must match `tech_reps.home_base`) to this MRO."""
    get_mro_location(mro_id, db)
    home_base = home_base.strip()
    if not home_base or len(home_base) > 200:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="home_base must be 1-200 characters"
        )
    travel = db.get(TravelTime, (home_base, mro_id))
    if travel is None:
        travel = TravelTime(home_base=home_base, mro_id=mro_id)
        db.add(travel)
    travel.travel_hours = payload.travel_hours
    travel.distance_km = payload.distance_km
    db.commit()
    return travel


@router.delete("/{mro_id}/travel-times/{home_base}", status_code=status.HTTP_204_NO_CONTENT)
def delete_travel_time(mro_id: int, home_base: str, db: DbSession) -> None:
    travel = db.get(TravelTime, (home_base.strip(), mro_id))
    if travel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Travel time not found")
    db.delete(travel)
    db.commit()
