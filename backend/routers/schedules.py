from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from database import DbSession
from schemas import ScheduleRunRequest, ScheduleRunResponse, SolveRequest, SolveResponse
from services import scheduler, solver

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/solve", response_model=SolveResponse)
def solve_schedule(payload: SolveRequest) -> SolveResponse:
    return solver.solve(payload)


@router.post("/run", response_model=ScheduleRunResponse)
def run_schedule(payload: ScheduleRunRequest, db: DbSession) -> ScheduleRunResponse:
    """Propose assignments for open demands in the window using stored data and CBA rules."""
    try:
        return scheduler.run(db, payload)
    except scheduler.NoActiveRulesError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Schedule changed while solving; run again",
        ) from None
