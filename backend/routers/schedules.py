from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from database import DbSession
from models import RepUnavailability
from schemas import ScheduleRunRequest, ScheduleRunResponse, SolveRequest, SolveResponse
from services import alert_scan, compliance, leave, scheduler, solver

router = APIRouter(prefix="/schedule", tags=["schedule"])

# Training due window for the alert scan that follows a saved run.
ALERT_TRAINING_DAYS = 60


@router.post("/solve", response_model=SolveResponse)
def solve_schedule(payload: SolveRequest) -> SolveResponse:
    return solver.solve(payload)


@router.post("/run", response_model=ScheduleRunResponse)
def run_schedule(payload: ScheduleRunRequest, db: DbSession) -> ScheduleRunResponse:
    """Propose assignments for open demands in the window using stored data and CBA rules.

    With save, each rep given work is checked for compliance, and the window is scanned
    for coverage gaps and shortages. Both write alerts.
    """
    try:
        result = scheduler.run(db, payload)
    except scheduler.NoActiveRulesError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Schedule changed while solving; run again",
        ) from None
    if payload.save:
        rep_ids = {p.rep_id for p in result.assignments}
        for entry_id in result.vacation_granted:
            entry = db.get(RepUnavailability, entry_id)
            leave.recount(db, entry.rep_id, range(entry.start_time.year, entry.end_time.year + 1))
            rep_ids.add(entry.rep_id)
        db.commit()
        for rep_id in sorted(rep_ids):
            result.violations.extend(
                compliance.record(db, rep_id, payload.start_time, payload.end_time)
            )
        alert_scan.scan(db, payload.start_time, payload.end_time, ALERT_TRAINING_DAYS)
    return result
