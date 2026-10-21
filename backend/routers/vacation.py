from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import TechRep, VacationBid
from schemas import (
    BidStatus,
    CsvImportResult,
    VacationAwardRequest,
    VacationAwardResult,
    VacationBidCreate,
    VacationBidRead,
    VacationBidUpdate,
    VacationCapacityWeek,
)
from services import compliance, leave, vacation
from services.csv_import import CSV_BODY, csv_rows, raise_row_errors, validation_message

router = APIRouter(prefix="/vacation", tags=["vacation"])

DUPLICATE_BID = (
    "Unknown tech rep, or the rep already bid on that week or preference rank"
)


@router.get("/bids", response_model=list[VacationBidRead])
def list_bids(
    db: DbSession,
    rep_id: int | None = None,
    year: int | None = None,
    status_filter: Annotated[BidStatus | None, Query(alias="status")] = None,
) -> list[VacationBid]:
    stmt = select(VacationBid).order_by(
        VacationBid.year, VacationBid.rep_id, VacationBid.preference_rank
    )
    if rep_id is not None:
        stmt = stmt.where(VacationBid.rep_id == rep_id)
    if year is not None:
        stmt = stmt.where(VacationBid.year == year)
    if status_filter is not None:
        stmt = stmt.where(VacationBid.status == status_filter)
    return list(db.scalars(stmt))


@router.get("/bids/{bid_id}", response_model=VacationBidRead)
def get_bid(bid_id: int, db: DbSession) -> VacationBid:
    bid = db.get(VacationBid, bid_id)
    if bid is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Vacation bid not found")
    return bid


@router.post(
    "/bids", response_model=VacationBidRead, status_code=status.HTTP_201_CREATED
)
def create_bid(payload: VacationBidCreate, db: DbSession) -> VacationBid:
    bid = VacationBid(**payload.model_dump())
    db.add(bid)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=DUPLICATE_BID) from None
    db.refresh(bid)
    return bid


@router.patch("/bids/{bid_id}", response_model=VacationBidRead)
def update_bid(bid_id: int, payload: VacationBidUpdate, db: DbSession) -> VacationBid:
    """Withdrawing or denying an awarded bid cancels its vacation leave."""
    bid = get_bid(bid_id, db)
    was_awarded = bid.status == "awarded"
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(bid, field, value)
    if was_awarded and bid.status != "awarded":
        leave.cancel_leave(db, bid.unavailability_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=DUPLICATE_BID) from None
    return bid


@router.delete("/bids/{bid_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bid(bid_id: int, db: DbSession) -> None:
    """Deleting an awarded bid cancels its vacation leave."""
    bid = get_bid(bid_id, db)
    if bid.status == "awarded":
        leave.cancel_leave(db, bid.unavailability_id)
    db.delete(bid)
    db.commit()


@router.post(
    "/bids/import",
    response_model=CsvImportResult,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=CSV_BODY,
)
def import_bids(
    rows: Annotated[list[tuple[int, dict[str, str]]], Depends(csv_rows)], db: DbSession
) -> CsvImportResult:
    """Import annual vacation bids from a text/csv body. All rows or none.

    Columns: rep_id or email, week_start (a Monday), preference_rank, and the optional
    year (defaults to the ISO year of week_start).
    """
    by_email = {
        r.email.lower(): r.id
        for r in db.scalars(select(TechRep).where(TechRep.email.is_not(None)))
    }
    bids: list[VacationBid] = []
    errors: list[tuple[int, str]] = []
    for line, row in rows:
        rep_id = row.get("rep_id") or by_email.get(row.get("email", "").lower())
        if not rep_id:
            errors.append(
                (line, f"Unknown rep {row.get('email') or row.get('rep_id')!r}")
            )
            continue
        fields = {
            "rep_id": rep_id,
            "week_start": row.get("week_start"),
            "preference_rank": row.get("preference_rank"),
            "year": row.get("year"),
        }
        try:
            if not fields["year"]:
                fields["year"] = (
                    date.fromisoformat(fields["week_start"]).isocalendar().year
                )
            payload = VacationBidCreate.model_validate(fields)
        except ValidationError as exc:
            errors.append((line, validation_message(exc)))
            continue
        except (TypeError, ValueError):
            errors.append((line, f"week_start: not a date: {fields['week_start']!r}"))
            continue
        bids.append(VacationBid(**payload.model_dump()))
    raise_row_errors(errors)

    db.add_all(bids)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=DUPLICATE_BID) from None
    return CsvImportResult(created=len(bids), ids=[b.id for b in bids])


@router.post("/award", response_model=VacationAwardResult)
def award_bids(payload: VacationAwardRequest, db: DbSession) -> VacationAwardResult:
    """Award the year's submitted bids in seniority order within the weekly cap and each
    rep's vacation balance. Awards become approved vacation leave."""
    result = vacation.award(db, payload.year)
    awarded_reps = {
        b.rep_id
        for b in db.scalars(
            select(VacationBid).where(VacationBid.id.in_(result.awarded))
        )
    }
    for rep_id in sorted(awarded_reps):
        compliance.record(db, rep_id, *leave.year_bounds(payload.year))
    return result


@router.get("/capacity", response_model=list[VacationCapacityWeek])
def vacation_capacity(
    db: DbSession, year: Annotated[int, Query(ge=2000, le=2100)]
) -> list[VacationCapacityWeek]:
    """Reps on approved vacation and places left under the cap, per week of the year."""
    return vacation.capacity(db, year)
