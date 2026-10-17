from datetime import date

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from database import DbSession
from models import CbaRules, PayPeriod, ShiftPattern, StatutoryHoliday
from schemas import (
    CbaRulesRead,
    CbaRulesUpdate,
    PayPeriodCreate,
    PayPeriodRead,
    ShiftPatternRead,
    StatutoryHolidayBase,
)
from services import scheduler

router = APIRouter(prefix="/cba", tags=["cba"])


@router.get("/rules", response_model=list[CbaRulesRead])
def list_rules(db: DbSession) -> list[CbaRules]:
    return list(db.scalars(select(CbaRules).order_by(CbaRules.effective_from)))


@router.get("/rules/active", response_model=CbaRulesRead)
def get_active_rules(db: DbSession, on: date | None = None) -> CbaRules:
    on = on or date.today()
    rules = scheduler.active_rules(db, on)
    if rules is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No CBA rules in effect on {on}")
    return rules


@router.patch("/rules/{rules_id}", response_model=CbaRulesRead)
def update_rules(rules_id: int, payload: CbaRulesUpdate, db: DbSession) -> CbaRules:
    rules = db.get(CbaRules, rules_id)
    if rules is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="CBA rules not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rules, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Update conflicts with another rule set (name or effective dates)",
        ) from None
    return rules


@router.get("/shift-patterns", response_model=list[ShiftPatternRead])
def list_shift_patterns(db: DbSession) -> list[ShiftPattern]:
    stmt = (
        select(ShiftPattern)
        .options(selectinload(ShiftPattern.start_windows))
        .order_by(ShiftPattern.code)
    )
    return list(db.scalars(stmt))


@router.get("/holidays", response_model=list[StatutoryHolidayBase])
def list_holidays(
    db: DbSession, start: date | None = None, end: date | None = None
) -> list[StatutoryHoliday]:
    stmt = select(StatutoryHoliday).order_by(StatutoryHoliday.holiday_date)
    if start:
        stmt = stmt.where(StatutoryHoliday.holiday_date >= start)
    if end:
        stmt = stmt.where(StatutoryHoliday.holiday_date <= end)
    return list(db.scalars(stmt))


@router.post(
    "/holidays", response_model=StatutoryHolidayBase, status_code=status.HTTP_201_CREATED
)
def create_holiday(payload: StatutoryHolidayBase, db: DbSession) -> StatutoryHoliday:
    holiday = StatutoryHoliday(**payload.model_dump())
    db.add(holiday)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="A holiday already exists on that date"
        ) from None
    return holiday


@router.get("/pay-periods", response_model=list[PayPeriodRead])
def list_pay_periods(
    db: DbSession, start: date | None = None, end: date | None = None
) -> list[PayPeriod]:
    """Pay periods overlapping [start, end). Dates with no row use semi-monthly periods."""
    stmt = select(PayPeriod).order_by(PayPeriod.start_date)
    if start:
        stmt = stmt.where(PayPeriod.end_date > start)
    if end:
        stmt = stmt.where(PayPeriod.start_date < end)
    return list(db.scalars(stmt))


@router.post("/pay-periods", response_model=PayPeriodRead, status_code=status.HTTP_201_CREATED)
def create_pay_period(payload: PayPeriodCreate, db: DbSession) -> PayPeriod:
    period = PayPeriod(**payload.model_dump())
    db.add(period)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Overlaps an existing pay period"
        ) from None
    return period


@router.delete("/pay-periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pay_period(period_id: int, db: DbSession) -> None:
    period = db.get(PayPeriod, period_id)
    if period is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pay period not found")
    db.delete(period)
    db.commit()
