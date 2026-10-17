from fastapi import FastAPI

from routers import (
    aircraft_types,
    assignments,
    cba,
    demands,
    mro_locations,
    reps,
    schedules,
    unavailability,
)

app = FastAPI(title="Tech Rep Scheduler API", version="0.1.0")

app.include_router(reps.router)
app.include_router(aircraft_types.router)
app.include_router(mro_locations.router)
app.include_router(cba.router)
app.include_router(unavailability.router)
app.include_router(demands.router)
app.include_router(assignments.router)
app.include_router(schedules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
