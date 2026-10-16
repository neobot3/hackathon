from pydantic import BaseModel, ConfigDict, Field


# Tech reps

class TechRepCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    home_base: str = Field(min_length=1, max_length=200)
    certified_aircraft_type_ids: list[int] = Field(default_factory=list, max_length=100)


class TechRepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    home_base: str
    active: bool
    certified_aircraft_type_ids: list[int]


# Scheduling solver

class RepInput(BaseModel):
    id: int
    certified_aircraft_type_ids: list[int] = Field(default_factory=list)


class RequestInput(BaseModel):
    id: int
    aircraft_type_id: int


class SolveRequest(BaseModel):
    reps: list[RepInput] = Field(max_length=500)
    requests: list[RequestInput] = Field(max_length=500)


class Assignment(BaseModel):
    request_id: int
    rep_id: int


class SolveResponse(BaseModel):
    status: str
    assignments: list[Assignment]
    unassigned_request_ids: list[int]
