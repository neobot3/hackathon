from fastapi import FastAPI

from routers import reps, schedules

app = FastAPI(title="Tech Rep Scheduler API", version="0.1.0")

app.include_router(reps.router)
app.include_router(schedules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
