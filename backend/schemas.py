from datetime import date, datetime, time
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

UnavailabilityReason = Literal[
    "vacation",
    "sick",
    "training",
    "bereavement",
    "parental",
    "union_leave",
    "unpaid_leave",
    "jury_duty",
    "other",
]
UnavailabilityStatus = Literal["requested", "approved", "denied", "cancelled"]
DemandType = Literal["base_coverage", "aog"]
DemandStatus = Literal["open", "filled", "cancelled"]
DemandResponseValue = Literal["accepted", "declined"]
AssignmentStatus = Literal["proposed", "confirmed", "in_progress", "completed", "cancelled"]
OvertimeType = Literal["none", "voluntary", "mandatory"]


class _TimeWindow(BaseModel):
    start_time: AwareDatetime
    end_time: AwareDatetime

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


# Tech reps

class TechRepCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    home_base: str = Field(min_length=1, max_length=200)
    classification: str | None = Field(default=None, max_length=60)
    cba_group: int | None = Field(default=None, ge=1, le=5)
    union_seniority_date: date | None = None
    shift_pattern_code: str | None = Field(default=None, max_length=10)
    shift_cycle_start: date | None = None
    banked_ot_hours: float = Field(default=0, ge=0, le=80)
    certified_aircraft_type_ids: list[int] = Field(default_factory=list, max_length=100)


class TechRepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    home_base: str
    active: bool
    classification: str | None
    cba_group: int | None
    union_seniority_date: date | None
    shift_pattern_code: str | None
    shift_cycle_start: date | None
    banked_ot_hours: float
    certified_aircraft_type_ids: list[int]


# CBA rules

class ShiftStartWindowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shift_name: str
    earliest_start: time
    latest_start: time


class ShiftPatternRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    description: str
    cycle: str
    shift_hours: float
    paid_meal_breaks: int
    cba_reference: str | None
    requires_consecutive_days_off: bool
    start_windows: list[ShiftStartWindowRead]


class CbaRulesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    effective_from: date
    effective_to: date | None
    min_rest_hours: float
    min_rest_hours_trade: float
    max_consecutive_scheduled_days: int
    max_consecutive_worked_days: int
    min_hours_off_per_set: float
    three_days_off_window_days: int
    avg_weekly_hours: float
    averaging_weeks_major_base: int
    averaging_weeks_other_base: int
    max_field_duty_hours: float
    post_field_rest_hours: float
    base_coverage_notice_hours: int
    max_vehicle_travel_km: int
    field_service_rate: float
    ot_rate_voluntary: float
    ot_voluntary_tier_hours: float
    ot_rate_voluntary_over_tier: float
    ot_rate_mandatory: float
    max_banked_ot_hours: float
    stat_holiday_rate: float
    major_bases: list[str]
    averaging_anchor_date: date | None
    consecutive_days_off_required: int
    aog_pay_buffer_hours: float


class StatutoryHolidayBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    holiday_date: date
    name: str = Field(min_length=1, max_length=100)


# Rep unavailability

class UnavailabilityCreate(_TimeWindow):
    rep_id: int
    reason: UnavailabilityReason
    status: UnavailabilityStatus = "approved"
    notes: str | None = Field(default=None, max_length=500)


class UnavailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rep_id: int
    reason: UnavailabilityReason
    start_time: datetime
    end_time: datetime
    status: UnavailabilityStatus
    notes: str | None


class UnavailabilityStatusUpdate(BaseModel):
    status: UnavailabilityStatus


# MRO demand

class DemandCreate(_TimeWindow):
    mro_id: int
    aircraft_type_id: int
    demand_type: DemandType = "base_coverage"
    reps_needed: int = Field(default=1, ge=1, le=50)
    priority: int = Field(default=3, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=500)


class DemandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mro_id: int
    aircraft_type_id: int
    demand_type: DemandType
    start_time: datetime
    end_time: datetime
    reps_needed: int
    priority: int
    status: DemandStatus
    notes: str | None


class DemandStatusUpdate(BaseModel):
    status: DemandStatus


class DemandResponseUpsert(BaseModel):
    response: DemandResponseValue


class DemandResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    demand_id: int
    rep_id: int
    response: DemandResponseValue
    responded_at: datetime


# Tech rep updates and certifications

class TechRepUpdate(BaseModel):
    """Only fields sent are changed; send null to clear an optional field."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    home_base: str | None = Field(default=None, min_length=1, max_length=200)
    active: bool | None = None
    classification: str | None = Field(default=None, max_length=60)
    cba_group: int | None = Field(default=None, ge=1, le=5)
    union_seniority_date: date | None = None
    shift_pattern_code: str | None = Field(default=None, max_length=10)
    shift_cycle_start: date | None = None
    banked_ot_hours: float | None = Field(default=None, ge=0, le=80)

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        for name in ("name", "home_base", "active", "banked_ot_hours"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class CertificationUpsert(BaseModel):
    certified_on: date | None = None
    expires_on: date | None = None

    @model_validator(mode="after")
    def _expires_after_certified(self) -> Self:
        if self.certified_on and self.expires_on and self.expires_on < self.certified_on:
            raise ValueError("expires_on must be on or after certified_on")
        return self


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    aircraft_type_id: int
    certified_on: date | None
    expires_on: date | None


# Reference data

class AircraftTypeCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)


class AircraftTypeRead(AircraftTypeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class MroLocationCreate(BaseModel):
    facility_name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)
    airport_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"Unknown IANA timezone: {value}") from None
        return value


class MroLocationRead(MroLocationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TravelTimeUpsert(BaseModel):
    travel_hours: float = Field(ge=0, le=24)
    distance_km: int | None = Field(default=None, ge=0)


class TravelTimeRead(TravelTimeUpsert):
    model_config = ConfigDict(from_attributes=True)

    home_base: str
    mro_id: int


class PayPeriodCreate(BaseModel):
    start_date: date
    # Exclusive.
    end_date: date

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class PayPeriodRead(PayPeriodCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


# Assignments

class AssignmentCreate(_TimeWindow):
    rep_id: int
    mro_id: int
    aircraft_type_id: int | None = None
    demand_id: int | None = None
    status: Literal["proposed", "confirmed"] = "proposed"
    overtime_type: OvertimeType = "none"
    overtime_hours: float = Field(default=0, ge=0, le=999)
    travel_hours: float = Field(default=0, ge=0, le=24)


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rep_id: int
    mro_id: int
    aircraft_type_id: int | None
    demand_id: int | None
    start_time: datetime
    end_time: datetime
    status: AssignmentStatus
    overtime_type: OvertimeType
    overtime_hours: float
    travel_hours: float
    created_at: datetime


class AssignmentStatusUpdate(BaseModel):
    status: AssignmentStatus


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


# Database-driven scheduling run

MAX_RUN_DAYS = 92


class ScheduleRunRequest(_TimeWindow):
    mro_id: int | None = None
    # When true, proposals are saved to assignments with status 'proposed'.
    save: bool = False
    # Assign reps who did not accept a solicited demand (21-2.09, 21-3.08).
    allow_mandatory: bool = False

    @model_validator(mode="after")
    def _limit_window(self) -> Self:
        if (self.end_time - self.start_time).days > MAX_RUN_DAYS:
            raise ValueError(f"Window must be {MAX_RUN_DAYS} days or less")
        return self


class ProposedAssignment(BaseModel):
    assignment_id: int | None = None
    demand_id: int
    rep_id: int
    mro_id: int
    start_time: datetime
    end_time: datetime
    field_service: bool
    mandatory: bool
    travel_hours: float
    paid_hours: float
    overtime_hours: float
    premium_hours: float


class UnfilledDemand(BaseModel):
    demand_id: int
    still_needed: int
    reason: str


class ScheduleRunResponse(BaseModel):
    status: str
    cba_rules_id: int
    assignments: list[ProposedAssignment]
    unfilled: list[UnfilledDemand]
    warnings: list[str] = Field(default_factory=list)
