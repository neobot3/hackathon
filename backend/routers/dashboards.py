from fastapi import APIRouter, HTTPException, status
from pydantic import AwareDatetime

from database import DbSession
from schemas import MAX_RUN_DAYS, CoverageWeek, WorkforceSummary
from services import dashboards

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _check_window(start: AwareDatetime, end: AwareDatetime) -> None:
    if end <= start or (end - start).days > MAX_RUN_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"end must be after start and within {MAX_RUN_DAYS} days",
        )


@router.get("/workforce", response_model=WorkforceSummary)
def workforce(
    db: DbSession, start: AwareDatetime, end: AwareDatetime, mro_id: int | None = None
) -> WorkforceSummary:
    """Available, assigned, and on-leave reps in [start, end)."""
    _check_window(start, end)
    return dashboards.workforce(db, start, end, mro_id)


@router.get("/coverage", response_model=list[CoverageWeek])
def coverage(
    db: DbSession, start: AwareDatetime, end: AwareDatetime, mro_id: int | None = None
) -> list[CoverageWeek]:
    """MRO staffing per week: seats needed, seats filled, and the gap."""
    _check_window(start, end)
    return dashboards.coverage(db, start, end, mro_id)
