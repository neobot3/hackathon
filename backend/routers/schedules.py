from fastapi import APIRouter

from schemas import SolveRequest, SolveResponse
from services import solver

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/solve", response_model=SolveResponse)
def solve_schedule(payload: SolveRequest) -> SolveResponse:
    return solver.solve(payload)
