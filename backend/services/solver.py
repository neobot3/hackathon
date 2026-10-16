from ortools.sat.python import cp_model

from config import settings
from schemas import Assignment, SolveRequest, SolveResponse


def solve(payload: SolveRequest) -> SolveResponse:
    # Placeholder model: match each request to at most one certified rep, one request per rep.
    # Availability, overtime, and CBA work/rest rules are still to be added.
    model = cp_model.CpModel()
    x: dict[tuple[int, int], cp_model.IntVar] = {}

    for rep in payload.reps:
        for req in payload.requests:
            if req.aircraft_type_id in rep.certified_aircraft_type_ids:
                x[rep.id, req.id] = model.new_bool_var(f"x_{rep.id}_{req.id}")

    for req in payload.requests:
        model.add_at_most_one(v for (_, q), v in x.items() if q == req.id)
    for rep in payload.reps:
        model.add_at_most_one(v for (r, _), v in x.items() if r == rep.id)

    model.maximize(sum(x.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = settings.solver_max_seconds
    result = solver.solve(model)

    assignments: list[Assignment] = []
    if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assignments = [
            Assignment(request_id=q, rep_id=r)
            for (r, q), v in x.items()
            if solver.value(v)
        ]

    assigned = {a.request_id for a in assignments}
    return SolveResponse(
        status=solver.status_name(result),
        assignments=assignments,
        unassigned_request_ids=[r.id for r in payload.requests if r.id not in assigned],
    )
