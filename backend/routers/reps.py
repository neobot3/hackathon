from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database import DbSession
from models import AircraftType, TechRep, TechRepCertification
from schemas import (
    CertificationRead,
    CertificationUpsert,
    TechRepCreate,
    TechRepRead,
    TechRepUpdate,
)

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
        classification=payload.classification,
        cba_group=payload.cba_group,
        union_seniority_date=payload.union_seniority_date,
        shift_pattern_code=payload.shift_pattern_code,
        shift_cycle_start=payload.shift_cycle_start,
        banked_ot_hours=payload.banked_ot_hours,
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
            detail="Email already in use, or unknown aircraft type ID or shift pattern",
        ) from None
    db.refresh(rep)
    return rep


@router.patch("/{rep_id}", response_model=TechRepRead)
def update_rep(rep_id: int, payload: TechRepUpdate, db: DbSession) -> TechRep:
    rep = get_rep(rep_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rep, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use or unknown shift pattern",
        ) from None
    return rep


@router.get("/{rep_id}/certifications", response_model=list[CertificationRead])
def list_certifications(rep_id: int, db: DbSession) -> list[TechRepCertification]:
    return get_rep(rep_id, db).certifications


@router.put(
    "/{rep_id}/certifications/{aircraft_type_id}", response_model=CertificationRead
)
def upsert_certification(
    rep_id: int, aircraft_type_id: int, payload: CertificationUpsert, db: DbSession
) -> TechRepCertification:
    get_rep(rep_id, db)
    if db.get(AircraftType, aircraft_type_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Aircraft type not found")
    cert = db.get(TechRepCertification, (rep_id, aircraft_type_id))
    if cert is None:
        cert = TechRepCertification(rep_id=rep_id, aircraft_type_id=aircraft_type_id)
        db.add(cert)
    cert.certified_on = payload.certified_on
    cert.expires_on = payload.expires_on
    db.commit()
    return cert


@router.delete(
    "/{rep_id}/certifications/{aircraft_type_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_certification(rep_id: int, aircraft_type_id: int, db: DbSession) -> None:
    cert = db.get(TechRepCertification, (rep_id, aircraft_type_id))
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Certification not found")
    db.delete(cert)
    db.commit()
