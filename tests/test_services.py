"""Service tests against the isolated Neon branch.

Writes stay inside the rolled-back test transaction.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from config.facility import DEFAULT_FACILITY_ID
from repositories.seed import seed_database
from services.exceptions import ConflictError, ValidationError
from services.factory import build_services
from services.results import FacilitySettingsUpdate
from services.unit_of_work import SqlAlchemyUnitOfWork

FACILITY_ID = DEFAULT_FACILITY_ID


def test_dashboard_matches_the_seeded_snapshot(db_session: Session) -> None:
    services = _services(db_session)
    snapshot = services.dashboard.snapshot(FACILITY_ID)
    counts = snapshot.counts
    assert (counts.total, counts.available, counts.occupied, counts.reserved, counts.unavailable) == (
        24,
        6,
        14,
        2,
        2,
    )
    assert counts.occupancy_percentage == Decimal("58.3")
    assert snapshot.rate_trend == "14/24 occupied"
    assert snapshot.active_sessions == 14
    assert snapshot.overstay_sessions == 1
    assert snapshot.above_high_occupancy_threshold is False
    assert snapshot.recent_gate_activity[0].id == "gl-1"
    assert sum(zone.capacity for zone in snapshot.zones) == 24
    assert sum(zone.occupied for zone in snapshot.zones) == 14
    assert sum(floor.capacity for floor in snapshot.floors) == 24

    spots = {spot.code: spot for spot in services.parking.summarize(FACILITY_ID).spots}
    assert spots["P-204"].status == "occupied"
    assert spots["P-204"].plate_number == "VEL-204X"
    assert spots["P-203"].status == "reserved"
    assert spots["P-208"].status == "unavailable"
    assert spots["P-210"].status == "available"
    assert spots["P-201"].hourly_rate == Decimal("6.00")
    assert spots["P-206"].hourly_rate == Decimal("4.80")
    assert spots["P-205"].hourly_rate == Decimal("4.20")
    assert spots["P-210"].hourly_rate == Decimal("3.50")
    found = services.parking.search_spots(FACILITY_ID, query="vel-204x", status="occupied")
    assert [spot.code for spot in found] == ["P-204"]


def test_historical_occupancy_comes_from_sessions(db_session: Session) -> None:
    services = _services(db_session)
    series = services.analytics.occupancy_over_time(
        FACILITY_ID,
        datetime(2026, 11, 25, 14, 0),
        datetime(2026, 11, 25, 15, 0),
    )
    assert series.has_history is True
    assert series.points[0].occupied == 12
    assert series.points[0].capacity == 24
    assert series.points[0].label == "2026-11-25 14:00"

    future = services.analytics.occupancy_over_time(
        FACILITY_ID,
        datetime(2026, 11, 25, 18, 0),
        datetime(2026, 11, 25, 19, 0),
    )
    assert future.has_history is False
    assert future.points == ()

    empty = services.analytics.occupancy_over_time(
        FACILITY_ID,
        datetime(2020, 1, 1, 8, 0),
        datetime(2020, 1, 1, 12, 0),
    )
    assert empty.has_history is False


def test_session_changes_roll_back_with_the_test_transaction(
    db_session: Session,
    migrated_engine,
) -> None:
    services = _services(db_session)
    started = services.sessions.start_session(FACILITY_ID, "SVC-100A", "P-210")
    assert started.gate_event.status == "Active"
    with migrated_engine.connect() as other:
        found = other.execute(
            text("SELECT id FROM parking_sessions WHERE id = :session_id"),
            {"session_id": started.session.id},
        ).first()
    assert found is None

    with pytest.raises(ConflictError) as occupied:
        services.sessions.start_session(FACILITY_ID, "SVC-200B", "P-210")
    assert occupied.value.code == "spot_occupied"
    active = services.sessions.list_active_sessions(FACILITY_ID)
    assert any(item.plate_number == "SVC-100A" for item in active)

    reserved = services.gate.record_entry(FACILITY_ID, "VIP-700S", "P-203")
    assert reserved.gate_event.status == "Reserved"
    with pytest.raises(ConflictError) as duplicate:
        services.sessions.start_session(FACILITY_ID, "VIP-700S", "P-202")
    assert duplicate.value.code == "vehicle_already_parked"

    finished = services.sessions.complete_session(
        FACILITY_ID,
        plate_number="SVC-100A",
        at=datetime(2026, 11, 25, 16, 24),
    )
    assert finished.quote is not None
    assert finished.quote.amount == Decimal("7.00")
    assert finished.quote.billable_hours == 2
    assert finished.session.status == "Completed"


def test_reservation_conflicts_and_settings_validation(db_session: Session) -> None:
    services = _services(db_session)
    with pytest.raises(ConflictError) as offline:
        services.reservations.create_reservation(
            FACILITY_ID,
            "SVC-300C",
            "P-208",
            datetime(2026, 11, 26, 9, 0),
            datetime(2026, 11, 26, 10, 0),
        )
    assert offline.value.code == "spot_unavailable"

    with pytest.raises(ConflictError) as overlap:
        services.reservations.create_reservation(
            FACILITY_ID,
            "SVC-300C",
            "P-203",
            datetime(2026, 11, 25, 15, 0),
            datetime(2026, 11, 25, 16, 0),
        )
    assert overlap.value.code == "reservation_overlap"

    with pytest.raises(ConflictError) as parked:
        services.reservations.create_reservation(
            FACILITY_ID,
            "SVC-300C",
            "P-204",
            datetime(2026, 11, 25, 14, 0),
            datetime(2026, 11, 25, 15, 0),
        )
    assert parked.value.code == "spot_occupied"

    created = services.reservations.create_reservation(
        FACILITY_ID,
        "SVC-300C",
        "P-210",
        datetime(2026, 11, 26, 9, 0),
        datetime(2026, 11, 26, 11, 0),
    )
    assert created.effective_status == "Scheduled"
    updated = services.reservations.update_reservation(
        FACILITY_ID,
        created.id,
        ends_at=datetime(2026, 11, 26, 12, 0),
    )
    assert updated.ends_at == datetime(2026, 11, 26, 12, 0)
    cancelled = services.reservations.cancel_reservation(FACILITY_ID, created.id)
    assert cancelled.status == "Cancelled"

    changed = services.settings.update_settings(
        FACILITY_ID,
        FacilitySettingsUpdate(operating_hours="24/7", grace_period_minutes=20),
    )
    assert changed.operating_hours == "24/7"
    assert changed.grace_period_minutes == 20
    with pytest.raises(ValidationError):
        services.settings.update_settings(
            FACILITY_ID,
            FacilitySettingsUpdate(hourly_rate=Decimal("0.00")),
        )
    current = services.settings.get_settings(FACILITY_ID)
    assert current.grace_period_minutes == 20
    assert current.hourly_rate == Decimal("4.20")
    entries = services.gate.list_activity(FACILITY_ID, direction="entry", limit=10)
    assert entries.total == 4


def _services(db_session: Session):
    seed_database(db_session)
    return build_services(lambda: SqlAlchemyUnitOfWork(db_session, lock_timeout_ms=3000))
