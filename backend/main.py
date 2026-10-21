from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import (
    aircraft_types,
    alerts,
    assignments,
    cba,
    dashboards,
    demands,
    leave_balances,
    maintenance_events,
    mro_locations,
    overtime,
    reps,
    schedules,
    training,
    unavailability,
    vacation,
)

app = FastAPI(title="Tech Rep Scheduler API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(reps.router)
app.include_router(aircraft_types.router)
app.include_router(mro_locations.router)
app.include_router(cba.router)
app.include_router(unavailability.router)
app.include_router(demands.router)
app.include_router(assignments.router)
app.include_router(schedules.router)
app.include_router(training.router)
app.include_router(leave_balances.router)
app.include_router(vacation.router)
app.include_router(maintenance_events.router)
app.include_router(alerts.router)
app.include_router(overtime.router)
app.include_router(dashboards.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
