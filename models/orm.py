"""Relational models for the Parkify facility.

Occupancy is not stored on a parking spot. An open parking session means the
spot is occupied, a maintenance reason means it is unavailable, and a
non-cancelled reservation that covers the facility clock means it is reserved.
Everything else is available.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Facility(Base, TimestampMixin):
    __tablename__ = "facilities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(180), nullable=False)
    operating_hours: Mapped[str] = mapped_column(String(80), nullable=False)
    simulated_date: Mapped[date] = mapped_column(Date, nullable=False)
    simulated_time: Mapped[time] = mapped_column(Time, nullable=False)
    snapshot_label: Mapped[str] = mapped_column(String(80), nullable=False)

    settings: Mapped[FacilitySettings] = relationship(
        back_populates="facility",
        uselist=False,
        cascade="all, delete-orphan",
    )
    floors: Mapped[list[Floor]] = relationship(
        back_populates="facility",
        cascade="all, delete-orphan",
    )


class FacilitySettings(Base, TimestampMixin):
    __tablename__ = "facility_settings"
    __table_args__ = (
        CheckConstraint("hourly_rate > 0", name="ck_facility_settings_hourly_rate"),
        CheckConstraint("daily_max_rate > 0", name="ck_facility_settings_daily_max"),
        CheckConstraint(
            "daily_max_rate >= hourly_rate",
            name="ck_facility_settings_daily_covers_hourly",
        ),
        CheckConstraint(
            "grace_period_minutes >= 0 AND grace_period_minutes <= 180",
            name="ck_facility_settings_grace_period",
        ),
        CheckConstraint("ev_surcharge >= 0", name="ck_facility_settings_ev_surcharge"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    facility_id: Mapped[str] = mapped_column(
        ForeignKey("facilities.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    daily_max_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(nullable=False)
    ev_surcharge: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    high_occupancy_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reservation_overstay_alert: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    space_fault_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    facility: Mapped[Facility] = relationship(back_populates="settings")


class Floor(Base, TimestampMixin):
    __tablename__ = "floors"
    __table_args__ = (
        UniqueConstraint("facility_id", "code", name="uq_floors_facility_code"),
        UniqueConstraint("facility_id", "level_index", name="uq_floors_facility_level"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    facility_id: Mapped[str] = mapped_column(
        ForeignKey("facilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    level_index: Mapped[int] = mapped_column(nullable=False)

    facility: Mapped[Facility] = relationship(back_populates="floors")
    zones: Mapped[list[ParkingZone]] = relationship(
        back_populates="floor",
        cascade="all, delete-orphan",
    )
    spots: Mapped[list[ParkingSpot]] = relationship(back_populates="floor")


class ParkingZone(Base, TimestampMixin):
    __tablename__ = "parking_zones"
    __table_args__ = (
        UniqueConstraint("floor_id", "code", name="uq_parking_zones_floor_code"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    floor_id: Mapped[str] = mapped_column(
        ForeignKey("floors.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    dashboard_category: Mapped[str] = mapped_column(String(32), nullable=False)
    accent: Mapped[str] = mapped_column(String(16), nullable=False)

    floor: Mapped[Floor] = relationship(back_populates="zones")
    spots: Mapped[list[ParkingSpot]] = relationship(back_populates="zone")


class ParkingSpot(Base, TimestampMixin):
    __tablename__ = "parking_spots"
    __table_args__ = (
        UniqueConstraint(
            "floor_id",
            "row",
            "slot_index",
            name="uq_parking_spots_floor_row_slot",
        ),
        CheckConstraint("row IN ('north', 'south')", name="ck_parking_spots_row"),
        CheckConstraint(
            "bay_class IN ('Standard', 'EV Fast 150kW', 'VIP Priority', 'Accessible')",
            name="ck_parking_spots_bay_class",
        ),
        CheckConstraint("hourly_rate > 0", name="ck_parking_spots_hourly_rate"),
        Index("ix_parking_spots_zone_id", "zone_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    floor_id: Mapped[str] = mapped_column(ForeignKey("floors.id"), nullable=False)
    zone_id: Mapped[str] = mapped_column(ForeignKey("parking_zones.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    row: Mapped[str] = mapped_column(String(16), nullable=False)
    slot_index: Mapped[int] = mapped_column(nullable=False)
    bay_class: Mapped[str] = mapped_column(String(32), nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    sensor_note: Mapped[str] = mapped_column(Text, nullable=False)
    maintenance_reason: Mapped[str | None] = mapped_column(String(120))

    floor: Mapped[Floor] = relationship(back_populates="spots")
    zone: Mapped[ParkingZone] = relationship(back_populates="spots")
    sessions: Mapped[list[ParkingSession]] = relationship(back_populates="spot")
    reservations: Mapped[list[Reservation]] = relationship(back_populates="spot")
    gate_activities: Mapped[list[GateActivity]] = relationship(back_populates="spot")


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    model: Mapped[str | None] = mapped_column(String(80))
    body_type: Mapped[str | None] = mapped_column(String(32))
    color_hex: Mapped[str | None] = mapped_column(String(16))
    accent_hex: Mapped[str | None] = mapped_column(String(16))
    driver_name: Mapped[str | None] = mapped_column(String(80))
    driver_initials: Mapped[str | None] = mapped_column(String(8))

    sessions: Mapped[list[ParkingSession]] = relationship(back_populates="vehicle")
    reservations: Mapped[list[Reservation]] = relationship(back_populates="vehicle")
    gate_activities: Mapped[list[GateActivity]] = relationship(back_populates="vehicle")


class ParkingSession(Base, TimestampMixin):
    __tablename__ = "parking_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Active', 'Completed')",
            name="ck_parking_sessions_status",
        ),
        CheckConstraint(
            "(status = 'Active' AND ended_at IS NULL) OR "
            "(status = 'Completed' AND ended_at IS NOT NULL AND ended_at >= started_at)",
            name="ck_parking_sessions_lifecycle",
        ),
        Index("ix_parking_sessions_vehicle_id", "vehicle_id"),
        Index("ix_parking_sessions_spot_id", "spot_id"),
        Index(
            "uq_parking_sessions_open_spot",
            "spot_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    spot_id: Mapped[str] = mapped_column(ForeignKey("parking_spots.id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    paid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    until_caption: Mapped[str | None] = mapped_column(String(80))
    monitoring_label: Mapped[str | None] = mapped_column(String(80))
    has_alert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    alert_title: Mapped[str | None] = mapped_column(String(80))
    alert_note: Mapped[str | None] = mapped_column(Text)

    spot: Mapped[ParkingSpot] = relationship(back_populates="sessions")
    vehicle: Mapped[Vehicle] = relationship(back_populates="sessions")


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Active', 'Scheduled', 'Completed', 'Cancelled')",
            name="ck_reservations_status",
        ),
        CheckConstraint("ends_at > starts_at", name="ck_reservations_window"),
        Index("ix_reservations_spot_starts", "spot_id", "starts_at"),
        Index("ix_reservations_vehicle_id", "vehicle_id"),
        ExcludeConstraint(
            (column("spot_id"), "="),
            (func.tsrange(column("starts_at"), column("ends_at"), "[)"), "&&"),
            where=text("status <> 'Cancelled'"),
            using="gist",
            name="ex_reservations_no_overlap",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    spot_id: Mapped[str] = mapped_column(ForeignKey("parking_spots.id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    is_seeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    spot: Mapped[ParkingSpot] = relationship(back_populates="reservations")
    vehicle: Mapped[Vehicle] = relationship(back_populates="reservations")
    gate_activities: Mapped[list[GateActivity]] = relationship(back_populates="reservation")


class GateActivity(Base, TimestampMixin):
    __tablename__ = "gate_activities"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('entry', 'exit')",
            name="ck_gate_activities_direction",
        ),
        CheckConstraint(
            "status IN ('Active', 'Completed', 'Reserved')",
            name="ck_gate_activities_status",
        ),
        Index("ix_gate_activities_occurred_at", "occurred_at"),
        Index("ix_gate_activities_spot_id", "spot_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    spot_id: Mapped[str] = mapped_column(ForeignKey("parking_spots.id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    reservation_id: Mapped[str | None] = mapped_column(ForeignKey("reservations.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    gate_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_label: Mapped[str | None] = mapped_column(String(32))

    spot: Mapped[ParkingSpot] = relationship(back_populates="gate_activities")
    vehicle: Mapped[Vehicle] = relationship(back_populates="gate_activities")
    reservation: Mapped[Reservation | None] = relationship(back_populates="gate_activities")


class User(Base):
    """An operator account. Public registration is not available.

    role is stored for later authorization. admin will have full access.
    employee will view occupancy and approve reservations, without financial
    or administrative access. Those checks are not enforced yet.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('admin', 'employee')", name="ck_users_role"),
        CheckConstraint("email = lower(email)", name="ck_users_email_normalized"),
        CheckConstraint("char_length(full_name) >= 2", name="ck_users_full_name"),
        CheckConstraint("char_length(password_hash) >= 20", name="ck_users_password_hash"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, role={self.role!r}, is_active={self.is_active!r})"
