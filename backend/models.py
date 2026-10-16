# Mirrors db/init.sql, which owns the schema.
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String, func
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


class TechRep(Base):
    __tablename__ = "tech_reps"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    home_base: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    rep: Mapped[TechRep] = relationship()
    mro: Mapped[MroLocation] = relationship()
    aircraft_type: Mapped[AircraftType | None] = relationship()
