from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database import DbSession
from models import TechRep, TechRepCertification
from schemas import TechRepCreate, TechRepRead

router = APIRouter(prefix="/reps", tags=["reps"])


@router.get("", response_model=list[TechRepRead])
def list_reps(db: DbSession) -> list[TechRep]:
    stmt = select(TechRep).options(selectinload(TechRep.certifications)).order_by(TechRep.id)
    return list(db.scalars(stmt))


@router.get("/{rep_id}", response_model=TechRepRead)
def get_rep(rep_id: int, db: DbSession) -> TechRep:
    rep = db.get(TechRep, rep_id, options=[selectinload(TechRep.certifications)])
    if rep is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tech rep not found")
    return rep


@router.post("", response_model=TechRepRead, status_code=status.HTTP_201_CREATED)
def create_rep(payload: TechRepCreate, db: DbSession) -> TechRep:
    rep = TechRep(
        name=payload.name,
        email=payload.email,
        home_base=payload.home_base,
        certifications=[
            TechRepCertification(aircraft_type_id=type_id)
            for type_id in set(payload.certified_aircraft_type_ids)
        ],
    )
    db.add(rep)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use or unknown aircraft type ID",
        ) from None
    db.refresh(rep)
    return rep
