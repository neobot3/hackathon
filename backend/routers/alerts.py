from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import Alert
from schemas import (
    MAX_RUN_DAYS,
    AlertCreate,
    AlertRead,
    AlertScanResult,
    AlertSeverity,
    AlertType,
    AlertUpdate,
)
from services import alert_scan

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/scan", response_model=AlertScanResult)
def scan_alerts(
    db: DbSession,
    start: AwareDatetime | None = None,
    end: AwareDatetime | None = None,
    training_days: Annotated[int, Query(ge=0, le=3650)] = 60,
) -> AlertScanResult:
    """Check [start, end) for coverage gaps, demands no rep is qualified for, and
    expected shortages, plus training due within training_days. Defaults to the next
    90 days. Earlier alerts of these types that no longer apply are acknowledged."""
    start = start or datetime.now(UTC)
    end = end or start + timedelta(days=90)
    if end <= start or (end - start).days > MAX_RUN_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"end must be after start and within {MAX_RUN_DAYS} days",
        )
    return alert_scan.scan(db, start, end, training_days)


@router.get("", response_model=list[AlertRead])
def list_alerts(
    db: DbSession,
    mro_id: int | None = None,
    rep_id: int | None = None,
    demand_id: int | None = None,
    alert_type: AlertType | None = None,
    severity: AlertSeverity | None = None,
    acknowledged: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[Alert]:
    """Newest first. Filter by location (mro_id), rep, demand, type, severity, and state."""
    stmt = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit)
    if mro_id is not None:
        stmt = stmt.where(Alert.mro_id == mro_id)
    if rep_id is not None:
        stmt = stmt.where(Alert.rep_id == rep_id)
    if demand_id is not None:
        stmt = stmt.where(Alert.demand_id == demand_id)
    if alert_type is not None:
        stmt = stmt.where(Alert.alert_type == alert_type)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if acknowledged is not None:
        stmt = stmt.where(Alert.acknowledged == acknowledged)
    return list(db.scalars(stmt))


@router.get("/{alert_id}", response_model=AlertRead)
def get_alert(alert_id: int, db: DbSession) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
def create_alert(payload: AlertCreate, db: DbSession) -> Alert:
    alert = Alert(**payload.model_dump())
    db.add(alert)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Unknown MRO, rep, demand, or assignment ID",
        ) from None
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}", response_model=AlertRead)
def update_alert(alert_id: int, payload: AlertUpdate, db: DbSession) -> Alert:
    alert = get_alert(alert_id, db)
    alert.acknowledged = payload.acknowledged
    db.commit()
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(alert_id: int, db: DbSession) -> None:
    db.delete(get_alert(alert_id, db))
    db.commit()
