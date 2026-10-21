from fastapi import APIRouter, HTTPException, status
from pydantic import AwareDatetime

from database import DbSession
from schemas import MAX_RUN_DAYS, OvertimeOpportunity
from services import overtime
from services.scheduler import NoActiveRulesError

router = APIRouter(prefix="/overtime", tags=["overtime"])


@router.get("/opportunities", response_model=list[OvertimeOpportunity])
def list_opportunities(
    db: DbSession, start: AwareDatetime, end: AwareDatetime, mro_id: int | None = None
) -> list[OvertimeOpportunity]:
    """Open demands in [start, end) still short of reps, with each rep who could take the
    work after checking certification, approved leave and training, and minimum rest."""
    if end <= start or (end - start).days > MAX_RUN_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"end must be after start and within {MAX_RUN_DAYS} days",
        )
    try:
        return overtime.opportunities(db, start, end, mro_id)
    except NoActiveRulesError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None
