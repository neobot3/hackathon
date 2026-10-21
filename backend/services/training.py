"""Training approval and due lists (BR3)."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    Assignment,
    MroLocation,
    RepTraining,
    RepUnavailability,
    TechRep,
    TechRepCertification,
    TrainingType,
)
from schemas import TrainingDue
from services.scheduler import home_tz

# Training runs in Calgary, or in Toronto for reps based in the east.
EASTERN_TIMEZONES = {
    "America/Toronto",
    "America/New_York",
    "America/Halifax",
    "America/Montreal",
}


def location(rep: TechRep, mros: list[MroLocation]) -> str:
    tz = home_tz(rep, mros)
    return "Toronto" if getattr(tz, "key", None) in EASTERN_TIMEZONES else "Calgary"


def certify(db: Session, record: RepTraining) -> None:
    """A completed endorsement course adds the aircraft type to the rep's certifications."""
    training_type = db.get(TrainingType, record.training_type_id)
    if (
        record.completed_on is None
        or training_type is None
        or training_type.aircraft_type_id is None
    ):
        return
    cert = db.get(TechRepCertification, (record.rep_id, training_type.aircraft_type_id))
    if cert is None:
        db.add(
            TechRepCertification(
                rep_id=record.rep_id,
                aircraft_type_id=training_type.aircraft_type_id,
                certified_on=record.completed_on,
            )
        )
    elif cert.certified_on is None or cert.certified_on > record.completed_on:
        cert.certified_on = record.completed_on


def approve(db: Session, record: RepTraining) -> list[int]:
    """Approve submitted dates: block the rep with a training leave row and cancel
    proposed assignments in the way. Returns the cancelled assignment IDs."""
    if record.unavailability_id is None:
        entry = RepUnavailability(
            rep_id=record.rep_id,
            reason="training",
            start_time=record.scheduled_start,
            end_time=record.scheduled_end,
            status="approved",
            notes=f"Training: {record.training_type.name}"[:500],
        )
        db.add(entry)
        db.flush()
        record.unavailability_id = entry.id
    record.status = "approved"
    clashes = list(
        db.scalars(
            select(Assignment).where(
                Assignment.rep_id == record.rep_id,
                Assignment.status == "proposed",
                Assignment.start_time < record.scheduled_end,
                Assignment.end_time > record.scheduled_start,
            )
        )
    )
    for a in clashes:
        a.status = "cancelled"
    return [a.id for a in clashes]


def due(db: Session, within_days: int) -> list[TrainingDue]:
    """Reps whose training expires within `within_days`, has expired, or (for mandatory
    training) was never completed. Training without an expiry is never due."""
    today = datetime.now(UTC).date()
    horizon = today + timedelta(days=within_days)
    types = {t.id: t for t in db.scalars(select(TrainingType))}
    reps = list(
        db.scalars(select(TechRep).where(TechRep.active).order_by(TechRep.name))
    )
    mros = list(db.scalars(select(MroLocation)))
    expiry: dict[tuple[int, int], date] = {}
    never_expires: set[tuple[int, int]] = set()
    next_session: dict[tuple[int, int], datetime] = {}
    now = datetime.now(UTC)
    for r in db.scalars(select(RepTraining)):
        key = (r.rep_id, r.training_type_id)
        if r.completed_on is not None:
            if r.expires_on is None:
                never_expires.add(key)
            else:
                expiry[key] = max(expiry.get(key, r.expires_on), r.expires_on)
        if (
            r.status in ("submitted", "approved")
            and r.scheduled_start is not None
            and r.scheduled_start >= now
        ):
            next_session[key] = min(
                next_session.get(key, r.scheduled_start), r.scheduled_start
            )

    out: list[TrainingDue] = []
    for rep in reps:
        for t in types.values():
            key = (rep.id, t.id)
            if key in never_expires:
                continue
            expires_on = expiry.get(key)
            if expires_on is None and not t.is_mandatory:
                continue
            if expires_on is not None and expires_on > horizon:
                continue
            out.append(
                TrainingDue(
                    rep_id=rep.id,
                    rep_name=rep.name,
                    training_type_id=t.id,
                    training_type_name=t.name,
                    is_mandatory=t.is_mandatory,
                    expires_on=expires_on,
                    days_left=None if expires_on is None else (expires_on - today).days,
                    next_scheduled_start=next_session.get(key),
                    location=location(rep, mros),
                )
            )
    out.sort(key=lambda d: (d.expires_on or date.min, d.rep_name))
    return out
