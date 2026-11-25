"""Parking rules shared by the services.

Occupancy is calculated when it is needed. It is not written back to a
parking spot. Timestamps are naive facility-local values, matching the
simulated Chicago clock stored on the facility.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from models.orm import ParkingSession, ParkingSpot, Reservation

SPOT_STATUSES = ("available", "occupied", "reserved", "unavailable")
HIGH_OCCUPANCY_THRESHOLD = Decimal("85.0")
EV_BAY_CLASS = "EV Fast 150kW"
STANDARD_BAY_CLASS = "Standard"


def normalize_search_token(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def matches_code_or_plate(code: str, plate_number: str | None, query: str | None) -> bool:
    if query is None or not query.strip():
        return True
    token = normalize_search_token(query)
    if not token:
        return True
    if token in normalize_search_token(code):
        return True
    return bool(plate_number) and token in normalize_search_token(plate_number)


def default_gate_name(spot_code: str) -> str:
    """Match the gate names the frontend assigns to new reservation entries."""
    if spot_code.startswith("P-2"):
        return "Skyline North A"
    return "South Express A"


def format_duration(delta: timedelta) -> str:
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours == 0:
        return f"{minutes}m"
    return f"{hours}h {minutes:02d}m"


def occupancy_percentage(occupied: int, total: int) -> Decimal:
    if total <= 0:
        return Decimal("0.0")
    return (Decimal(occupied) * Decimal(100) / Decimal(total)).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )


def derive_status(
    spot: ParkingSpot,
    open_session: ParkingSession | None,
    covering_reservation: Reservation | None,
) -> str:
    """Apply the existing precedence: occupied, unavailable, reserved, available."""
    if open_session is not None and open_session.ended_at is None:
        return "occupied"
    if spot.maintenance_reason:
        return "unavailable"
    if (
        covering_reservation is not None
        and covering_reservation.status != "Cancelled"
    ):
        return "reserved"
    return "available"


def reservation_covers(reservation: Reservation, moment: datetime) -> bool:
    return (
        reservation.status != "Cancelled"
        and reservation.starts_at <= moment < reservation.ends_at
    )


def effective_reservation_status(reservation: Reservation, moment: datetime) -> str:
    """Status a caller should display. Completed and Cancelled stay as stored."""
    if reservation.status == "Cancelled":
        return "Cancelled"
    if reservation.status == "Completed":
        return "Completed"
    if reservation.ends_at <= moment:
        return "Completed"
    if reservation.starts_at <= moment:
        return "Active"
    return "Scheduled"


def initial_reservation_status(starts_at: datetime, ends_at: datetime, moment: datetime) -> str:
    if ends_at <= moment:
        return "Completed"
    if starts_at <= moment:
        return "Active"
    return "Scheduled"


def apply_reservation_lifecycle(reservation: Reservation, moment: datetime) -> str:
    """Move an open reservation to the status implied by the facility clock."""
    if reservation.status in {"Cancelled", "Completed"}:
        return reservation.status
    reservation.status = effective_reservation_status(reservation, moment)
    return reservation.status


def session_blocks_reservation(
    session: ParkingSession,
    starts_at: datetime,
    ends_at: datetime,
    moment: datetime,
) -> bool:
    """Decide whether an open session conflicts with a reservation window.

    A window that contains the facility clock always conflicts, because the
    spot is occupied now. A same-day window that starts before the session's
    displayed paid-until time also conflicts. That second check is the rule
    used by the reservation form. A later window on another day is allowed,
    because the form does not treat an open session as a permanent hold.
    """
    if session.ended_at is not None:
        return False
    if starts_at <= moment < ends_at:
        return True
    paid_until = session.paid_until
    if paid_until is None:
        return False
    return (
        starts_at.date() == paid_until.date()
        and starts_at < paid_until
        and ends_at > session.started_at
    )


def session_covers_instant(
    session: ParkingSession,
    moment: datetime,
    *,
    clock: datetime,
) -> bool:
    """Whether a stored session occupies a spot at one facility-local instant.

    A completed session covers `started_at <= moment < ended_at`. An open
    session covers `started_at <= moment <= clock` and is not extended past
    the facility clock.
    """
    if moment < session.started_at:
        return False
    if session.ended_at is not None:
        return moment < session.ended_at
    return moment <= clock
