"""Values returned by services.

These are copies of the fields a later controller needs. They are not
SQLAlchemy objects, so they stay valid after the transaction closes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from models.orm import GateActivity, ParkingSession, Reservation


@dataclass(frozen=True)
class SpotAvailability:
    spot_id: str
    code: str
    floor_id: str
    floor_code: str
    zone_id: str
    zone_code: str
    zone_name: str
    bay_class: str
    status: str
    hourly_rate: Decimal
    maintenance_reason: str | None
    plate_number: str | None
    session_id: str | None
    reservation_id: str | None
    reserved_until: datetime | None


@dataclass(frozen=True)
class OccupancyCounts:
    total: int
    available: int
    occupied: int
    reserved: int
    unavailable: int
    occupancy_percentage: Decimal


@dataclass(frozen=True)
class ZoneOccupancy:
    zone_id: str
    code: str
    name: str
    category: str
    floor_id: str
    floor_code: str
    occupied: int
    reserved: int
    unavailable: int
    available: int
    capacity: int


@dataclass(frozen=True)
class FloorOccupancy:
    floor_id: str
    code: str
    name: str
    occupied: int
    reserved: int
    unavailable: int
    available: int
    capacity: int


@dataclass(frozen=True)
class FacilityOccupancy:
    counts: OccupancyCounts
    floors: tuple[FloorOccupancy, ...]
    zones: tuple[ZoneOccupancy, ...]
    spots: tuple[SpotAvailability, ...]


@dataclass(frozen=True)
class ParkingQuote:
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    duration_label: str
    hourly_rate: Decimal
    billable_hours: int
    amount: Decimal
    grace_applied: bool
    daily_maximum: Decimal


@dataclass(frozen=True)
class SessionView:
    id: str
    spot_id: str
    spot_code: str
    vehicle_id: str
    plate_number: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    paid_until: datetime | None
    has_alert: bool
    alert_title: str | None


@dataclass(frozen=True)
class GateEventView:
    id: str
    occurred_at: datetime
    plate_number: str
    direction: str
    gate_name: str
    spot_code: str
    zone_code: str
    status: str
    duration_label: str | None
    reservation_id: str | None


@dataclass(frozen=True)
class SessionChange:
    session: SessionView
    gate_event: GateEventView
    quote: ParkingQuote | None = None


@dataclass(frozen=True)
class ReservationView:
    id: str
    spot_id: str
    spot_code: str
    vehicle_id: str
    plate_number: str
    driver_name: str | None
    status: str
    effective_status: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class FacilitySettingsView:
    facility_id: str
    facility_name: str
    facility_address: str
    operating_hours: str
    hourly_rate: Decimal
    daily_max_rate: Decimal
    grace_period_minutes: int
    ev_surcharge: Decimal
    high_occupancy_alert: bool
    reservation_overstay_alert: bool
    space_fault_alert: bool


@dataclass(frozen=True)
class FacilitySettingsUpdate:
    """Fields omitted from an update stay at their stored values."""

    facility_name: str | None = None
    facility_address: str | None = None
    operating_hours: str | None = None
    hourly_rate: Decimal | None = None
    daily_max_rate: Decimal | None = None
    grace_period_minutes: int | None = None
    ev_surcharge: Decimal | None = None
    high_occupancy_alert: bool | None = None
    reservation_overstay_alert: bool | None = None
    space_fault_alert: bool | None = None


@dataclass(frozen=True)
class DashboardSnapshot:
    facility_id: str
    facility_name: str
    snapshot_time: datetime
    counts: OccupancyCounts
    rate_trend: str
    active_sessions: int
    overstay_sessions: int
    high_occupancy_alert_armed: bool
    high_occupancy_threshold_percent: Decimal
    above_high_occupancy_threshold: bool
    reservation_overstay_alert_armed: bool
    space_fault_alert_armed: bool
    floors: tuple[FloorOccupancy, ...]
    zones: tuple[ZoneOccupancy, ...]
    recent_gate_activity: tuple[GateEventView, ...]


@dataclass(frozen=True)
class OccupancyPoint:
    start: datetime
    end: datetime
    label: str
    occupied: int
    capacity: int
    occupancy_percentage: Decimal


@dataclass(frozen=True)
class OccupancySeries:
    definition: str
    has_history: bool
    points: tuple[OccupancyPoint, ...]


@dataclass(frozen=True)
class GatePage:
    items: tuple[GateEventView, ...]
    total: int
    limit: int
    offset: int


def session_view(session: ParkingSession, *, spot_code: str, plate_number: str) -> SessionView:
    return SessionView(
        id=session.id,
        spot_id=session.spot_id,
        spot_code=spot_code,
        vehicle_id=session.vehicle_id,
        plate_number=plate_number,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        paid_until=session.paid_until,
        has_alert=bool(session.has_alert),
        alert_title=session.alert_title,
    )


def gate_event_view(activity: GateActivity, *, zone_code: str | None = None) -> GateEventView:
    resolved_zone = zone_code
    if resolved_zone is None and activity.spot is not None and activity.spot.zone is not None:
        resolved_zone = activity.spot.zone.code
    plate = activity.vehicle.plate_number if activity.vehicle is not None else ""
    spot_code = activity.spot.code if activity.spot is not None else ""
    return GateEventView(
        id=activity.id,
        occurred_at=activity.occurred_at,
        plate_number=plate,
        direction=activity.direction,
        gate_name=activity.gate_name,
        spot_code=spot_code,
        zone_code=resolved_zone or "",
        status=activity.status,
        duration_label=activity.duration_label,
        reservation_id=activity.reservation_id,
    )


def reservation_view(
    reservation: Reservation,
    *,
    spot_code: str,
    plate_number: str,
    driver_name: str | None,
    effective_status: str,
) -> ReservationView:
    return ReservationView(
        id=reservation.id,
        spot_id=reservation.spot_id,
        spot_code=spot_code,
        vehicle_id=reservation.vehicle_id,
        plate_number=plate_number,
        driver_name=driver_name,
        status=reservation.status,
        effective_status=effective_status,
        starts_at=reservation.starts_at,
        ends_at=reservation.ends_at,
    )


@dataclass(frozen=True)
class UserAccount:
    """An operator account without the password hash."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
