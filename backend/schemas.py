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
DemandType = Literal[
    "base_coverage",
    "aog",
    "heavy_check",
    "induction",
    "rts",
    "lease_return",
    "hard_landing",
    "hail_damage",
    "mro_support",
]
DemandStatus = Literal["open", "filled", "cancelled"]
DemandResponseValue = Literal["accepted", "declined"]
AssignmentStatus = Literal["proposed", "confirmed", "in_progress", "completed", "cancelled"]
OvertimeType = Literal["none", "voluntary", "mandatory"]
# Digits with optional +, spaces, dots, dashes, and brackets, e.g. (437) 995-6452.
PHONE_PATTERN = r"^[0-9+() .-]{7,30}$"
TrainingStatus = Literal["submitted", "approved", "rejected"]
LeaveType = Literal["vacation", "stat", "sick"]
BidStatus = Literal["submitted", "awarded", "denied", "withdrawn"]
MaintenanceEventType = Literal[
    "heavy_check",
    "induction",
    "rts",
    "aog",
    "lease_return",
    "hard_landing",
    "hail_damage",
    "mro_support",
]
MaintenanceEventStatus = Literal["planned", "in_progress", "completed", "cancelled"]
AlertType = Literal[
    "coverage_gap",
    "no_qualified_rep",
    "shortage",
    "date_conflict",
    "training_due",
    "training_expired",
    "training_conflict",
    "vacation_limit",
    "sick_limit",
    "rest",
    "shift_pattern",
    "qualification",
    "seniority",
    "no_aircraft",
    "schedule_horizon",
    "vacation_unused",
]
AlertSeverity = Literal["info", "warning", "critical"]


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown IANA timezone: {value}") from None
    return value


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
    seniority_rank: int | None = Field(default=None, ge=1)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
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
    seniority_rank: int | None
    phone: str | None
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
    min_days_off_between_rotations: int
    max_reps_off_per_week: int
    continuity_lookback_days: int
    schedule_publish_days: int


# Bounds mirror the Numeric/SmallInteger column sizes in models.CbaRules.
class CbaRulesUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    effective_from: date | None = None
    effective_to: date | None = None
    min_rest_hours: float | None = Field(default=None, ge=0, le=99.99)
    min_rest_hours_trade: float | None = Field(default=None, ge=0, le=99.99)
    max_consecutive_scheduled_days: int | None = Field(default=None, ge=1, le=365)
    max_consecutive_worked_days: int | None = Field(default=None, ge=1, le=365)
    min_hours_off_per_set: float | None = Field(default=None, ge=0, le=999.99)
    three_days_off_window_days: int | None = Field(default=None, ge=1, le=365)
    avg_weekly_hours: float | None = Field(default=None, ge=0, le=99.99)
    averaging_weeks_major_base: int | None = Field(default=None, ge=1, le=52)
    averaging_weeks_other_base: int | None = Field(default=None, ge=1, le=52)
    max_field_duty_hours: float | None = Field(default=None, ge=0, le=99.99)
    post_field_rest_hours: float | None = Field(default=None, ge=0, le=99.99)
    base_coverage_notice_hours: int | None = Field(default=None, ge=0, le=32767)
    max_vehicle_travel_km: int | None = Field(default=None, ge=0, le=32767)
    field_service_rate: float | None = Field(default=None, ge=0, le=9.99)
    ot_rate_voluntary: float | None = Field(default=None, ge=0, le=9.99)
    ot_voluntary_tier_hours: float | None = Field(default=None, ge=0, le=99.99)
    ot_rate_voluntary_over_tier: float | None = Field(default=None, ge=0, le=9.99)
    ot_rate_mandatory: float | None = Field(default=None, ge=0, le=9.99)
    max_banked_ot_hours: float | None = Field(default=None, ge=0, le=999.99)
    stat_holiday_rate: float | None = Field(default=None, ge=0, le=9.99)
    major_bases: list[str] | None = Field(default=None, max_length=50)
    averaging_anchor_date: date | None = None
    consecutive_days_off_required: int | None = Field(default=None, ge=0, le=14)
    aog_pay_buffer_hours: float | None = Field(default=None, ge=0, le=99.99)
    min_days_off_between_rotations: int | None = Field(default=None, ge=0, le=14)
    max_reps_off_per_week: int | None = Field(default=None, ge=0, le=1000)
    continuity_lookback_days: int | None = Field(default=None, ge=0, le=3650)
    schedule_publish_days: int | None = Field(default=None, ge=0, le=365)

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        nullable = {"effective_to", "averaging_anchor_date"}
        for name in self.model_fields_set - nullable:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class StatutoryHolidayBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    holiday_date: date
    name: str = Field(min_length=1, max_length=100)


class SickLeaveAllowanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month: int
    max_days: float
    needs_review: bool


class SickLeaveAllowanceUpdate(BaseModel):
    max_days: float = Field(ge=0, le=365)


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
    maintenance_event_id: int | None = None


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
    maintenance_event_id: int | None


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
    seniority_rank: int | None = Field(default=None, ge=1)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)

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


class AircraftTypeUpdate(BaseModel):
    model_name: str | None = Field(default=None, min_length=1, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        if "model_name" in self.model_fields_set and self.model_name is None:
            raise ValueError("model_name cannot be null")
        return self


class MroLocationCreate(BaseModel):
    facility_name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)
    airport_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    timezone: str = Field(default="UTC", max_length=64)
    # Home base whose team covers this MRO.
    covering_base: str | None = Field(default=None, max_length=200)

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        return _check_timezone(value)


class MroLocationRead(MroLocationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class MroLocationUpdate(BaseModel):
    facility_name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    airport_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    timezone: str | None = Field(default=None, max_length=64)
    covering_base: str | None = Field(default=None, max_length=200)

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        return value if value is None else _check_timezone(value)

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        for name in ("facility_name", "location", "timezone"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


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


def _reject_nulls(model: BaseModel, names: tuple[str, ...]) -> None:
    for name in names:
        if name in model.model_fields_set and getattr(model, name) is None:
            raise ValueError(f"{name} cannot be null")


# Training

class TrainingTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # None for one-off training.
    recurrence_months: int | None = Field(default=None, ge=1, le=120)
    is_mandatory: bool = True
    # Endorsement courses: completing one certifies the rep on this aircraft type.
    aircraft_type_id: int | None = None


class TrainingTypeRead(TrainingTypeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TrainingTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    recurrence_months: int | None = Field(default=None, ge=1, le=120)
    is_mandatory: bool | None = None
    aircraft_type_id: int | None = None

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        _reject_nulls(self, ("name", "is_mandatory"))
        return self


class _TrainingDates(BaseModel):
    completed_on: date | None = None
    expires_on: date | None = None
    scheduled_start: AwareDatetime | None = None
    scheduled_end: AwareDatetime | None = None
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        start, end = self.scheduled_start, self.scheduled_end
        if start and end and end <= start:
            raise ValueError("scheduled_end must be after scheduled_start")
        if self.completed_on and self.expires_on and self.expires_on < self.completed_on:
            raise ValueError("expires_on must be on or after completed_on")
        return self


class RepTrainingCreate(_TrainingDates):
    """expires_on defaults to completed_on plus the type's recurrence."""

    rep_id: int
    training_type_id: int

    @model_validator(mode="after")
    def _dates_together(self) -> Self:
        if (self.scheduled_start is None) != (self.scheduled_end is None):
            raise ValueError("scheduled_start and scheduled_end go together")
        return self


class RepTrainingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rep_id: int
    training_type_id: int
    completed_on: date | None
    expires_on: date | None
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    status: TrainingStatus
    unavailability_id: int | None
    notes: str | None


class RepTrainingUpdate(_TrainingDates):
    """Only fields sent are changed."""


# Leave balances

class LeaveBalanceUpsert(BaseModel):
    entitled_days: float = Field(ge=0, le=999.99)
    used_days: float = Field(default=0, ge=0, le=999.99)


class LeaveBalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rep_id: int
    year: int
    leave_type: LeaveType
    entitled_days: float
    used_days: float
    remaining_days: float


# Vacation bids

class VacationBidCreate(BaseModel):
    rep_id: int
    year: int = Field(ge=2000, le=2100)
    week_start: date
    preference_rank: int = Field(ge=1, le=52)

    @field_validator("week_start")
    @classmethod
    def _monday(cls, value: date) -> date:
        if value.isoweekday() != 1:
            raise ValueError("week_start must be a Monday")
        return value


class VacationBidRead(VacationBidCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: BidStatus
    unavailability_id: int | None


class VacationBidUpdate(BaseModel):
    preference_rank: int | None = Field(default=None, ge=1, le=52)
    status: BidStatus | None = None

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        _reject_nulls(self, ("preference_rank", "status"))
        return self


class VacationAwardRequest(BaseModel):
    year: int = Field(ge=2000, le=2100)


class VacationAwardDenied(BaseModel):
    bid_id: int
    rep_id: int
    week_start: date
    reason: str


class VacationAwardResult(BaseModel):
    year: int
    awarded: list[int]
    denied: list[VacationAwardDenied]


class VacationCapacityWeek(BaseModel):
    week_start: date
    cap: int
    reps_off: int
    remaining: int
    rep_ids: list[int]


class TrainingDue(BaseModel):
    rep_id: int
    rep_name: str
    training_type_id: int
    training_type_name: str
    is_mandatory: bool
    # None when the rep has never completed this training.
    expires_on: date | None
    days_left: int | None
    # Next submitted or approved session for this training, if any.
    next_scheduled_start: datetime | None
    # Calgary, or Toronto for eastern-based reps.
    location: str


# Maintenance events

class MaintenanceEventCreate(BaseModel):
    aircraft_type_id: int
    mro_id: int
    tail_number: str = Field(min_length=1, max_length=10)
    event_type: MaintenanceEventType
    induction_date: date
    rts_date: date
    # Left out: the recommended staffing for the event type.
    reps_required: int | None = Field(default=None, ge=1, le=50)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _rts_after_induction(self) -> Self:
        if self.rts_date < self.induction_date:
            raise ValueError("rts_date must be on or after induction_date")
        return self


class MaintenanceEventRead(MaintenanceEventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reps_required: int
    status: MaintenanceEventStatus
    created_at: datetime


class MaintenanceEventWithDemands(MaintenanceEventRead):
    # Live demands generated for the event, one per support shift.
    demand_ids: list[int] = Field(default_factory=list)


class MaintenanceEventUpdate(BaseModel):
    tail_number: str | None = Field(default=None, min_length=1, max_length=10)
    induction_date: date | None = None
    rts_date: date | None = None
    reps_required: int | None = Field(default=None, ge=1, le=50)
    status: MaintenanceEventStatus | None = None
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        _reject_nulls(
            self, ("tail_number", "induction_date", "rts_date", "reps_required", "status")
        )
        return self


class CsvImportResult(BaseModel):
    created: int
    ids: list[int]


# Alerts

class AlertCreate(BaseModel):
    alert_type: AlertType
    severity: AlertSeverity = "warning"
    mro_id: int | None = None
    rep_id: int | None = None
    demand_id: int | None = None
    assignment_id: int | None = None
    message: str = Field(min_length=1, max_length=500)


class AlertRead(AlertCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    acknowledged: bool


class AlertUpdate(BaseModel):
    acknowledged: bool


class AlertScanResult(BaseModel):
    created: int
    resolved: int


# Dashboards

class WorkforceRep(BaseModel):
    rep_id: int
    name: str
    home_base: str
    status: Literal["assigned", "on_leave", "available"]
    mro_ids: list[int]
    leave_reasons: list[str]
    assigned_hours: float


class WorkforceSummary(BaseModel):
    start: datetime
    end: datetime
    available: int
    assigned: int
    on_leave: int
    reps: list[WorkforceRep]


class CoverageWeek(BaseModel):
    mro_id: int
    week_start: date
    shifts: int
    seats_needed: int
    seats_filled: int
    gap: int


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


class AssignmentUpdate(BaseModel):
    """Only fields sent are changed. Rep and times can change on live assignments."""

    status: AssignmentStatus | None = None
    rep_id: int | None = None
    start_time: AwareDatetime | None = None
    end_time: AwareDatetime | None = None

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        _reject_nulls(self, ("status", "rep_id", "start_time", "end_time"))
        return self


class ComplianceWarning(BaseModel):
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    rep_id: int
    mro_id: int | None = None
    demand_id: int | None = None
    assignment_id: int | None = None


class AssignmentWithWarnings(AssignmentRead):
    warnings: list[ComplianceWarning] = Field(default_factory=list)


class TrainingApproval(RepTrainingRead):
    cancelled_assignment_ids: list[int] = Field(default_factory=list)
    warnings: list[ComplianceWarning] = Field(default_factory=list)


class TrainingRejection(BaseModel):
    # Sent back to the training department with the record.
    note: str | None = Field(default=None, max_length=400)


# Overtime

class EligibleRep(BaseModel):
    rep_id: int
    name: str
    seniority_rank: int | None
    # Reply to a solicitation for this demand, if any.
    response: DemandResponseValue | None
    field_service: bool
    # True when the rep is based at the MRO's covering base; that team is asked first.
    home_team: bool
    # True when the demand falls on a shift pattern day off; None without a pattern.
    pattern_day_off: bool | None


class IneligibleRep(BaseModel):
    rep_id: int
    name: str
    reason: str


class OvertimeOpportunity(BaseModel):
    demand_id: int
    mro_id: int
    aircraft_type_id: int
    demand_type: DemandType
    start_time: datetime
    end_time: datetime
    priority: int
    reps_needed: int
    still_needed: int
    # Most senior first: the order to offer voluntary overtime. Mandatory overtime
    # goes from the end of the list (reverse seniority).
    eligible: list[EligibleRep]
    ineligible: list[IneligibleRep]


class Reassignment(BaseModel):
    rep_id: int
    name: str
    seniority_rank: int | None
    # The lower-priority work the rep would move off.
    assignment_id: int
    from_mro_id: int
    from_demand_id: int | None
    from_priority: int | None


class EventStaffingOption(OvertimeOpportunity):
    reassignments: list[Reassignment]


class EventStaffingOptions(BaseModel):
    event_id: int
    demands: list[EventStaffingOption]


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

MAX_RUN_DAYS = 366


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
    # Requested vacation (rep_unavailability IDs) granted within the weekly cap, or not.
    # With save, granted requests are approved.
    vacation_granted: list[int] = Field(default_factory=list)
    vacation_not_granted: list[int] = Field(default_factory=list)
    # Compliance findings on the saved schedule; also written to alerts.
    violations: list[ComplianceWarning] = Field(default_factory=list)
