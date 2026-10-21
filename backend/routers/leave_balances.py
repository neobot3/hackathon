from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select

from database import DbSession
from models import LeaveBalance, TechRep
from schemas import LeaveBalanceRead, LeaveBalanceUpsert, LeaveType

router = APIRouter(prefix="/leave-balances", tags=["leave balances"])

Year = Annotated[int, Path(ge=2000, le=2100)]


@router.get("", response_model=list[LeaveBalanceRead])
def list_leave_balances(
    db: DbSession,
    rep_id: int | None = None,
    year: int | None = None,
    leave_type: LeaveType | None = None,
) -> list[LeaveBalance]:
    stmt = select(LeaveBalance).order_by(
        LeaveBalance.rep_id, LeaveBalance.year, LeaveBalance.leave_type
    )
    if rep_id is not None:
        stmt = stmt.where(LeaveBalance.rep_id == rep_id)
    if year is not None:
        stmt = stmt.where(LeaveBalance.year == year)
    if leave_type is not None:
        stmt = stmt.where(LeaveBalance.leave_type == leave_type)
    return list(db.scalars(stmt))


@router.put("/{rep_id}/{year}/{leave_type}", response_model=LeaveBalanceRead)
def upsert_leave_balance(
    rep_id: int,
    year: Year,
    leave_type: LeaveType,
    payload: LeaveBalanceUpsert,
    db: DbSession,
) -> LeaveBalance:
    if db.get(TechRep, rep_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tech rep not found")
    balance = db.get(LeaveBalance, (rep_id, year, leave_type))
    if balance is None:
        balance = LeaveBalance(rep_id=rep_id, year=year, leave_type=leave_type)
        db.add(balance)
    balance.entitled_days = payload.entitled_days
    balance.used_days = payload.used_days
    db.commit()
    db.refresh(balance)
    return balance


@router.delete("/{rep_id}/{year}/{leave_type}", status_code=status.HTTP_204_NO_CONTENT)
def delete_leave_balance(
    rep_id: int, year: Year, leave_type: LeaveType, db: DbSession
) -> None:
    balance = db.get(LeaveBalance, (rep_id, year, leave_type))
    if balance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Leave balance not found")
    db.delete(balance)
    db.commit()
