# Mirrors db/init.sql, which owns the schema.
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AircraftType(Base):
    __tablename__ = "aircraft_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), unique=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100))


class MroLocation(Base):
    __tablename__ = "mro_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    facility_name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    airport_code: Mapped[str | None] = mapped_column(String(3))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    covering_base: Mapped[str | None] = mapped_column(String(200))


class ShiftPattern(Base):
    __tablename__ = "shift_patterns"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    description: Mapped[str] = mapped_column(String(200))
    cycle: Mapped[str] = mapped_column(String(56))
    shift_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    paid_meal_breaks: Mapped[int] = mapped_column(SmallInteger, default=0)
    cba_reference: Mapped[str | None] = mapped_column(String(20))
    requires_consecutive_days_off: Mapped[bool] = mapped_column(default=False)

    start_windows: Mapped[list["ShiftStartWindow"]] = relationship(
        order_by="ShiftStartWindow.earliest_start"
    )


class ShiftStartWindow(Base):
    __tablename__ = "shift_start_windows"

    shift_pattern_code: Mapped[str] = mapped_column(
        ForeignKey("shift_patterns.code", ondelete="CASCADE"), primary_key=True
    )
    shift_name: Mapped[str] = mapped_column(String(20), primary_key=True)
    earliest_start: Mapped[time]
    latest_start: Mapped[time]


class CbaRules(Base):
    __tablename__ = "cba_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]

    min_rest_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    min_rest_hours_trade: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    max_consecutive_scheduled_days: Mapped[int] = mapped_column(SmallInteger)
    max_consecutive_worked_days: Mapped[int] = mapped_column(SmallInteger)
    min_hours_off_per_set: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    three_days_off_window_days: Mapped[int] = mapped_column(SmallInteger)
    avg_weekly_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    averaging_weeks_major_base: Mapped[int] = mapped_column(SmallInteger)
    averaging_weeks_other_base: Mapped[int] = mapped_column(SmallInteger)

    max_field_duty_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    post_field_rest_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    base_coverage_notice_hours: Mapped[int] = mapped_column(SmallInteger)
    max_vehicle_travel_km: Mapped[int] = mapped_column(SmallInteger)
    field_service_rate: Mapped[Decimal] = mapped_column(Numeric(3, 2))

    ot_rate_voluntary: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    ot_voluntary_tier_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    ot_rate_voluntary_over_tier: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    ot_rate_mandatory: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    max_banked_ot_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    stat_holiday_rate: Mapped[Decimal] = mapped_column(Numeric(3, 2))

    major_bases: Mapped[list[str]] = mapped_column(ARRAY(Text))
    averaging_anchor_date: Mapped[date | None]
    consecutive_days_off_required: Mapped[int] = mapped_column(SmallInteger)
    aog_pay_buffer_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    min_days_off_between_rotations: Mapped[int] = mapped_column(SmallInteger)
    max_reps_off_per_week: Mapped[int] = mapped_column(SmallInteger)
    continuity_lookback_days: Mapped[int] = mapped_column(SmallInteger)
    schedule_publish_days: Mapped[int] = mapped_column(SmallInteger)


class SickLeaveAllowance(Base):
    __tablename__ = "sick_leave_allowance"

    month: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    max_days: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    needs_review: Mapped[bool] = mapped_column(default=True)


class PayPeriod(Base):
    __tablename__ = "pay_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date]
    end_date: Mapped[date]


class TravelTime(Base):
    __tablename__ = "travel_times"

    home_base: Mapped[str] = mapped_column(String(200), primary_key=True)
    mro_id: Mapped[int] = mapped_column(
        ForeignKey("mro_locations.id", ondelete="CASCADE"), primary_key=True
    )
    travel_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    distance_km: Mapped[int | None]


class StatutoryHoliday(Base):
    __tablename__ = "statutory_holidays"

    holiday_date: Mapped[date] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class TechRep(Base):
    __tablename__ = "tech_reps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    home_base: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(default=True)
    classification: Mapped[str | None] = mapped_column(String(60))
    cba_group: Mapped[int | None] = mapped_column(SmallInteger)
    union_seniority_date: Mapped[date | None]
    shift_pattern_code: Mapped[str | None] = mapped_column(
        ForeignKey("shift_patterns.code", ondelete="RESTRICT")
    )
    shift_cycle_start: Mapped[date | None]
    banked_ot_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    seniority_rank: Mapped[int | None]
    phone: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    shift_pattern: Mapped[ShiftPattern | None] = relationship()
    certifications: Mapped[list["TechRepCertification"]] = relationship(
        back_populates="rep", cascade="all, delete-orphan"
    )

    @property
    def certified_aircraft_type_ids(self) -> list[int]:
        return [c.aircraft_type_id for c in self.certifications]


class TechRepCertification(Base):
    __tablename__ = "tech_rep_certifications"

    rep_id: Mapped[int] = mapped_column(
        ForeignKey("tech_reps.id", ondelete="CASCADE"), primary_key=True
    )
    aircraft_type_id: Mapped[int] = mapped_column(
        ForeignKey("aircraft_types.id", ondelete="CASCADE"), primary_key=True
    )
    certified_on: Mapped[date | None]
    expires_on: Mapped[date | None]

    rep: Mapped[TechRep] = relationship(back_populates="certifications")
    aircraft_type: Mapped[AircraftType] = relationship()


class RepUnavailability(Base):
    __tablename__ = "rep_unavailability"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("tech_reps.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(20))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="approved")
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MroDemand(Base):
    __tablename__ = "mro_demands"

    id: Mapped[int] = mapped_column(primary_key=True)
    mro_id: Mapped[int] = mapped_column(ForeignKey("mro_locations.id", ondelete="RESTRICT"))
    aircraft_type_id: Mapped[int] = mapped_column(
        ForeignKey("aircraft_types.id", ondelete="RESTRICT")
    )
    demand_type: Mapped[str] = mapped_column(String(20), default="base_coverage")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reps_needed: Mapped[int] = mapped_column(SmallInteger, default=1)
    priority: Mapped[int] = mapped_column(SmallInteger, default=3)
    status: Mapped[str] = mapped_column(String(20), default="open")
    notes: Mapped[str | None] = mapped_column(String(500))
    maintenance_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("maintenance_events.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DemandResponse(Base):
    __tablename__ = "demand_responses"

    demand_id: Mapped[int] = mapped_column(
        ForeignKey("mro_demands.id", ondelete="CASCADE"), primary_key=True
    )
    rep_id: Mapped[int] = mapped_column(
        ForeignKey("tech_reps.id", ondelete="CASCADE"), primary_key=True
    )
    response: Mapped[str] = mapped_column(String(10))
    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("tech_reps.id", ondelete="RESTRICT"))
    mro_id: Mapped[int] = mapped_column(ForeignKey("mro_locations.id", ondelete="RESTRICT"))
    aircraft_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("aircraft_types.id", ondelete="SET NULL")
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    demand_id: Mapped[int | None] = mapped_column(
        ForeignKey("mro_demands.id", ondelete="SET NULL")
    )
    overtime_type: Mapped[str] = mapped_column(String(10), default="none")
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    travel_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal(0))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    rep: Mapped[TechRep] = relationship()
    mro: Mapped[MroLocation] = relationship()
    aircraft_type: Mapped[AircraftType | None] = relationship()


class TrainingType(Base):
    __tablename__ = "training_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    recurrence_months: Mapped[int | None] = mapped_column(SmallInteger)
    is_mandatory: Mapped[bool] = mapped_column(default=True)
    aircraft_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("aircraft_types.id", ondelete="SET NULL")
    )


class RepTraining(Base):
    __tablename__ = "rep_training"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("tech_reps.id", ondelete="CASCADE"))
    training_type_id: Mapped[int] = mapped_column(
        ForeignKey("training_types.id", ondelete="RESTRICT")
    )
    completed_on: Mapped[date | None]
    expires_on: Mapped[date | None]
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    unavailability_id: Mapped[int | None] = mapped_column(
        ForeignKey("rep_unavailability.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    training_type: Mapped[TrainingType] = relationship()


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    rep_id: Mapped[int] = mapped_column(
        ForeignKey("tech_reps.id", ondelete="CASCADE"), primary_key=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    leave_type: Mapped[str] = mapped_column(String(10), primary_key=True)
    entitled_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))
    used_days: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0))

    @property
    def remaining_days(self) -> Decimal:
        return self.entitled_days - self.used_days


class VacationBid(Base):
    __tablename__ = "vacation_bids"

    id: Mapped[int] = mapped_column(primary_key=True)
    rep_id: Mapped[int] = mapped_column(ForeignKey("tech_reps.id", ondelete="CASCADE"))
    year: Mapped[int] = mapped_column(SmallInteger)
    week_start: Mapped[date]
    preference_rank: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    unavailability_id: Mapped[int | None] = mapped_column(
        ForeignKey("rep_unavailability.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MaintenanceEvent(Base):
    __tablename__ = "maintenance_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    aircraft_type_id: Mapped[int] = mapped_column(
        ForeignKey("aircraft_types.id", ondelete="RESTRICT")
    )
    mro_id: Mapped[int] = mapped_column(ForeignKey("mro_locations.id", ondelete="RESTRICT"))
    tail_number: Mapped[str] = mapped_column(String(10))
    event_type: Mapped[str] = mapped_column(String(20))
    induction_date: Mapped[date]
    rts_date: Mapped[date]
    reps_required: Mapped[int] = mapped_column(SmallInteger, default=1)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(10), default="warning")
    mro_id: Mapped[int | None] = mapped_column(ForeignKey("mro_locations.id", ondelete="CASCADE"))
    rep_id: Mapped[int | None] = mapped_column(ForeignKey("tech_reps.id", ondelete="CASCADE"))
    demand_id: Mapped[int | None] = mapped_column(ForeignKey("mro_demands.id", ondelete="CASCADE"))
    assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE")
    )
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    acknowledged: Mapped[bool] = mapped_column(default=False)
