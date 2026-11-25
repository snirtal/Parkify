"""Service tests that do not open a database connection."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from unittest.mock import MagicMock

import pytest

from models.orm import (
    Facility,
    FacilitySettings,
    Floor,
    ParkingSession,
    ParkingSpot,
    ParkingZone,
    Reservation,
    Vehicle,
)
from repositories.spots import SqlAlchemyParkingSpotRepository
from services.analytics import OCCUPANCY_SERIES_DEFINITION
from services.exceptions import ConflictError, ValidationError
from services.factory import build_services
from services.pricing import PricingService
from services.results import FacilitySettingsUpdate, FacilitySettingsView
from services.rules import derive_status, session_blocks_reservation
from services.settings import validate_facility_settings
from services.support import FixedClock
from tests.service_fakes import MemoryRepositories, MemoryUnitOfWork, add_settings

CLOCK = datetime(2026, 11, 25, 14, 24)
DAY = datetime(2026, 11, 25)


def test_service_modules_do_not_import_flask() -> None:
    for path in Path("services").glob("*.py"):
        tree = ast.parse(path.read_text())
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        assert "flask" not in imported
        assert "sqlalchemy" not in imported or path.name == "unit_of_work.py"


def test_get_for_update_requests_a_row_lock() -> None:
    session = MagicMock()
    session.get.return_value = None
    repository = SqlAlchemyParkingSpotRepository(session)
    assert repository.get_for_update("bay-p210") is None
    session.get.assert_called_once_with(ParkingSpot, "bay-p210", with_for_update=True)


def test_occupancy_precedence() -> None:
    spot = _spot("spot-a", "P-A", maintenance_reason=None)
    open_session = ParkingSession(
        id="ses-open",
        spot_id=spot.id,
        vehicle_id="veh-1",
        status="Active",
        started_at=CLOCK,
    )
    reservation = Reservation(
        id="res-a",
        spot_id=spot.id,
        vehicle_id="veh-2",
        status="Active",
        starts_at=CLOCK,
        ends_at=CLOCK + timedelta(hours=1),
    )
    assert derive_status(spot, open_session, reservation) == "occupied"
    spot.maintenance_reason = "Calibration"
    assert derive_status(spot, open_session, reservation) == "occupied"
    assert derive_status(spot, None, reservation) == "unavailable"
    spot.maintenance_reason = None
    assert derive_status(spot, None, reservation) == "reserved"
    reservation.status = "Cancelled"
    assert derive_status(spot, None, None) == "available"


def test_active_session_blocks_a_window_that_covers_now_or_paid_until() -> None:
    session = ParkingSession(
        id="ses-open",
        spot_id="spot-a",
        vehicle_id="veh-1",
        status="Active",
        started_at=datetime(2026, 11, 25, 8, 0),
        paid_until=datetime(2026, 11, 25, 18, 30),
    )
    assert session_blocks_reservation(
        session,
        datetime(2026, 11, 25, 14, 0),
        datetime(2026, 11, 25, 15, 0),
        CLOCK,
    )
    assert session_blocks_reservation(
        session,
        datetime(2026, 11, 25, 16, 0),
        datetime(2026, 11, 25, 17, 0),
        CLOCK,
    )
    assert not session_blocks_reservation(
        session,
        datetime(2026, 11, 25, 19, 0),
        datetime(2026, 11, 25, 20, 0),
        CLOCK,
    )
    assert not session_blocks_reservation(
        session,
        datetime(2026, 11, 26, 9, 0),
        datetime(2026, 11, 26, 10, 0),
        CLOCK,
    )


def test_pricing_boundaries() -> None:
    pricing = PricingService()
    settings = _settings()
    standard = _spot("spot-s", "P-S", bay_class="Standard", hourly_rate=Decimal("9.99"))
    electric = _spot("spot-e", "P-E", bay_class="EV Fast 150kW", hourly_rate=Decimal("1.00"))
    vip = _spot("spot-v", "P-V", bay_class="VIP Priority", hourly_rate=Decimal("6.00"))
    accessible = _spot("spot-a", "P-A", bay_class="Accessible", hourly_rate=Decimal("3.50"))

    assert pricing.displayed_hourly_rate(standard, settings) == Decimal("4.20")
    assert pricing.displayed_hourly_rate(electric, settings) == Decimal("4.80")
    assert pricing.displayed_hourly_rate(vip, settings) == Decimal("6.00")
    assert pricing.displayed_hourly_rate(accessible, settings) == Decimal("3.50")

    start = datetime(2026, 11, 25, 10, 0)
    free = pricing.quote(standard, settings, start, start + timedelta(minutes=15))
    assert free.grace_applied is True
    assert free.amount == Decimal("0.00")
    assert free.billable_hours == 0

    one_hour = pricing.quote(standard, settings, start, start + timedelta(minutes=15, microseconds=1))
    assert one_hour.grace_applied is False
    assert one_hour.billable_hours == 1
    assert one_hour.amount == Decimal("4.20")

    exact_hour = pricing.quote(standard, settings, start, start + timedelta(hours=1))
    assert exact_hour.billable_hours == 1
    assert exact_hour.amount == Decimal("4.20")

    next_hour = pricing.quote(standard, settings, start, start + timedelta(hours=1, seconds=1))
    assert next_hour.billable_hours == 2
    assert next_hour.amount == Decimal("8.40")

    capped = pricing.quote(standard, settings, start, start + timedelta(hours=7))
    assert capped.billable_hours == 7
    assert capped.amount == Decimal("28.00")

    electric_cap = pricing.quote(electric, settings, start, start + timedelta(hours=6))
    assert electric_cap.hourly_rate == Decimal("4.80")
    assert electric_cap.amount == Decimal("28.00")

    vip_quote = pricing.quote(vip, settings, start, start + timedelta(hours=1))
    assert vip_quote.amount == Decimal("6.00")

    two_days = pricing.quote(
        standard,
        settings,
        datetime(2026, 11, 25, 0, 0),
        datetime(2026, 11, 27, 0, 0),
    )
    assert two_days.amount == Decimal("56.00")

    with pytest.raises(ValidationError):
        pricing.quote(standard, settings, start, start - timedelta(minutes=1))


def test_pricing_rejects_aware_timestamps() -> None:
    aware = datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        PricingService().quote(_spot("spot-s", "P-S"), _settings(), aware, aware)


def test_settings_validation_matches_the_screen_bounds() -> None:
    valid = _settings_view()
    assert validate_facility_settings(valid).hourly_rate == Decimal("4.20")
    assert validate_facility_settings(
        _settings_view(operating_hours="24/7")
    ).operating_hours == "24/7"

    with pytest.raises(ValidationError, match="Hourly"):
        validate_facility_settings(_settings_view(hourly_rate=Decimal("0.00")))
    with pytest.raises(ValidationError, match="500.00"):
        validate_facility_settings(_settings_view(hourly_rate=Decimal("500.01")))
    with pytest.raises(ValidationError, match="Daily maximum"):
        validate_facility_settings(
            _settings_view(hourly_rate=Decimal("10.00"), daily_max_rate=Decimal("9.00"))
        )
    with pytest.raises(ValidationError, match="grace"):
        validate_facility_settings(_settings_view(grace_period_minutes=181))
    with pytest.raises(ValidationError, match="EV"):
        validate_facility_settings(_settings_view(ev_surcharge=Decimal("100.01")))
    with pytest.raises(ValidationError, match="Facility name"):
        validate_facility_settings(_settings_view(facility_name="A"))
    with pytest.raises(ValidationError, match="Operating hours"):
        validate_facility_settings(_settings_view(operating_hours="am"))


def test_search_and_dashboard_use_derived_status() -> None:
    services, store = _services()
    found = services.parking.search_spots("facility-test", query="vel 204")
    assert [spot.code for spot in found] == ["P-OCC"]
    assert found[0].status == "occupied"
    unavailable = services.parking.search_spots("facility-test", status="unavailable")
    assert [spot.code for spot in unavailable] == ["P-OFF"]
    reserved = services.parking.search_spots("facility-test", zone_code="T-N", status="reserved")
    assert [spot.code for spot in reserved] == ["P-HOLD"]
    summary = services.parking.summarize("facility-test")
    assert (summary.counts.occupied, summary.counts.reserved, summary.counts.unavailable, summary.counts.available) == (
        1,
        1,
        1,
        1,
    )
    assert summary.counts.occupancy_percentage == Decimal("25.0")
    snapshot = services.dashboard.snapshot("facility-test")
    assert snapshot.active_sessions == 1
    assert snapshot.overstay_sessions == 1
    assert snapshot.above_high_occupancy_threshold is False
    assert snapshot.recent_gate_activity[0].plate_number == "VEL-204X"
    assert snapshot.zones[0].capacity == 4
    assert store.locks == []


def test_entry_exit_reservation_and_rollback() -> None:
    services, store = _services()
    entered = services.gate.record_entry("facility-test", "NEW-100", "P-FREE")
    assert entered.gate_event.status == "Active"
    assert entered.gate_event.direction == "entry"
    assert store.locks[0] == ("spot", "spot-free")
    assert store.locks[1][0] == "vehicle"

    with pytest.raises(ConflictError) as occupied:
        services.gate.record_entry("facility-test", "OTHER-1", "P-OCC")
    assert occupied.value.code == "spot_occupied"

    with pytest.raises(ConflictError) as offline:
        services.gate.record_entry("facility-test", "OTHER-1", "P-OFF")
    assert offline.value.code == "spot_unavailable"

    with pytest.raises(ConflictError) as reserved:
        services.gate.record_entry("facility-test", "OTHER-1", "P-HOLD")
    assert reserved.value.code == "spot_reserved"

    holder = services.gate.record_entry("facility-test", "HOLD-1", "P-HOLD")
    assert holder.gate_event.status == "Reserved"
    finished = services.sessions.complete_session(
        "facility-test",
        plate_number="NEW-100",
        at=CLOCK + timedelta(hours=2),
    )
    assert finished.quote is not None
    assert finished.quote.amount == Decimal("8.40")
    assert finished.gate_event.direction == "exit"
    assert finished.session.status == "Completed"
    with pytest.raises(ConflictError) as duplicate:
        services.sessions.start_session("facility-test", "HOLD-1", "P-FREE")
    assert duplicate.value.code == "vehicle_already_parked"

    created = services.reservations.create_reservation(
        "facility-test",
        "BOOK-1",
        "P-FREE",
        datetime(2026, 11, 26, 9, 0),
        datetime(2026, 11, 26, 11, 0),
    )
    assert created.effective_status == "Scheduled"
    with pytest.raises(ConflictError) as overlap:
        services.reservations.create_reservation(
            "facility-test",
            "BOOK-2",
            "P-FREE",
            datetime(2026, 11, 26, 10, 0),
            datetime(2026, 11, 26, 12, 0),
        )
    assert overlap.value.code == "reservation_overlap"
    with pytest.raises(ConflictError):
        services.reservations.create_reservation(
            "facility-test",
            "BOOK-1",
            "P-OCC",
            datetime(2026, 11, 26, 9, 0),
            datetime(2026, 11, 26, 10, 0),
        )
    cancelled = services.reservations.cancel_reservation("facility-test", created.id)
    assert cancelled.status == "Cancelled"
    assert len(store.gate_activities.values()) == 4


def test_failed_commit_rolls_back_the_session_and_gate_event() -> None:
    services, store = _failing_services()
    before = len(store.sessions.values())
    with pytest.raises(ConflictError) as failure:
        services.sessions.start_session("facility-test", "ROLL-1", "P-FREE")
    assert failure.value.code == "concurrent_update"
    assert len(store.sessions.values()) == before
    assert all(activity.vehicle_id != "pending" for activity in store.gate_activities.values())
    assert all(vehicle.plate_number != "ROLL-1" for vehicle in store.vehicles.values())


def test_analytics_does_not_invent_history_or_project_open_sessions() -> None:
    services, _store = _services()
    empty = services.analytics.occupancy_over_time(
        "facility-test",
        datetime(2020, 1, 1, 0, 0),
        datetime(2020, 1, 1, 3, 0),
    )
    assert empty.has_history is False
    assert empty.points == ()
    assert empty.definition == OCCUPANCY_SERIES_DEFINITION

    future = services.analytics.occupancy_over_time(
        "facility-test",
        datetime(2026, 11, 25, 18, 0),
        datetime(2026, 11, 25, 20, 0),
    )
    assert future.has_history is False

    history = services.analytics.occupancy_over_time(
        "facility-test",
        datetime(2026, 11, 25, 14, 0),
        datetime(2026, 11, 25, 15, 0),
    )
    assert history.has_history is True
    assert history.points[0].label == "2026-11-25 14:00"
    assert history.points[0].occupied == 1
    assert "Now" not in history.points[0].label


def test_reservation_update_locks_the_current_vehicle_and_both_spots() -> None:
    services, store = _services()
    services.reservations.update_reservation(
        "facility-test",
        "res-hold",
        ends_at=datetime(2026, 11, 25, 17, 0),
    )
    assert store.locks == [("spot", "spot-hold"), ("vehicle", "veh-holder")]

    services, store = _services()
    services.reservations.update_reservation(
        "facility-test",
        "res-hold",
        spot_code="P-FREE",
        ends_at=datetime(2026, 11, 25, 17, 0),
    )
    assert store.locks == [
        ("spot", "spot-free"),
        ("spot", "spot-hold"),
        ("vehicle", "veh-holder"),
    ]


def test_expired_reservation_can_be_refreshed_but_not_edited() -> None:
    services, _store = _services()
    created = services.reservations.create_reservation(
        "facility-test",
        "PAST-1",
        "P-FREE",
        datetime(2026, 11, 25, 8, 0),
        datetime(2026, 11, 25, 9, 0),
    )
    assert created.effective_status == "Completed"
    with pytest.raises(ConflictError) as closed:
        services.reservations.cancel_reservation("facility-test", created.id)
    assert closed.value.code == "reservation_closed"


def _services():
    store = _world()
    services = build_services(lambda: MemoryUnitOfWork(store), clock=FixedClock(CLOCK), ids=_ids())
    return services, store


def _failing_services():
    store = _world()
    services = build_services(
        lambda: MemoryUnitOfWork(store, fail_commit=True),
        clock=FixedClock(CLOCK),
        ids=_ids(),
    )
    return services, store


def _ids():
    counter = {"value": 0}

    def factory(prefix: str) -> str:
        counter["value"] += 1
        return f"{prefix}-{counter['value']}"

    return factory


def _world() -> MemoryRepositories:
    store = MemoryRepositories()
    facility = Facility(
        id="facility-test",
        name="Test Hub",
        address="1 Test Street",
        operating_hours="00:00 – 23:59 (24/7)",
        simulated_date=CLOCK.date(),
        simulated_time=CLOCK.time(),
        snapshot_label="test",
    )
    floor = Floor(
        id="floor-test",
        facility_id=facility.id,
        code="T1",
        name="Test deck",
        level_index=1,
    )
    zone = ParkingZone(
        id="zone-test",
        floor_id=floor.id,
        code="T-N",
        name="Test north",
        category="Test",
        dashboard_category="Standard",
        accent="blue",
    )
    store.facilities.add(facility)
    add_settings(store, _settings())
    specs = (
        ("spot-occ", "P-OCC", None),
        ("spot-off", "P-OFF", "Calibration"),
        ("spot-hold", "P-HOLD", None),
        ("spot-free", "P-FREE", None),
    )
    spots = {}
    for index, (spot_id, code, maintenance) in enumerate(specs):
        spot = _spot(spot_id, code, maintenance_reason=maintenance)
        spot.floor_id = floor.id
        spot.zone_id = zone.id
        spot.slot_index = index
        spot.floor = floor
        spot.zone = zone
        spots[spot_id] = spot
        store.spots.add(spot)

    parked = Vehicle(id="veh-parked", plate_number="VEL-204X")
    holder = Vehicle(id="veh-holder", plate_number="HOLD-1")
    store.vehicles.add(parked)
    store.vehicles.add(holder)
    open_session = ParkingSession(
        id="ses-open",
        spot_id="spot-occ",
        vehicle_id=parked.id,
        status="Active",
        started_at=datetime(2026, 11, 25, 8, 0),
        paid_until=datetime(2026, 11, 25, 14, 8),
        has_alert=False,
    )
    open_session.spot = spots["spot-occ"]
    open_session.vehicle = parked
    finished = ParkingSession(
        id="ses-done",
        spot_id="spot-free",
        vehicle_id=parked.id,
        status="Completed",
        started_at=datetime(2026, 11, 25, 9, 0),
        ended_at=datetime(2026, 11, 25, 10, 0),
        has_alert=False,
    )
    finished.spot = spots["spot-free"]
    finished.vehicle = parked
    store.sessions.add(open_session)
    store.sessions.add(finished)
    reservation = Reservation(
        id="res-hold",
        spot_id="spot-hold",
        vehicle_id=holder.id,
        status="Active",
        starts_at=datetime(2026, 11, 25, 14, 0),
        ends_at=datetime(2026, 11, 25, 16, 0),
        is_seeded=False,
    )
    reservation.spot = spots["spot-hold"]
    reservation.vehicle = holder
    store.reservations.add(reservation)
    from models.orm import GateActivity

    activity = GateActivity(
        id="gl-1",
        spot_id="spot-occ",
        vehicle_id=parked.id,
        occurred_at=CLOCK,
        direction="entry",
        gate_name="Skyline North A",
        status="Active",
    )
    activity.spot = spots["spot-occ"]
    activity.vehicle = parked
    store.gate_activities.add(activity)
    return store


def _spot(spot_id: str, code: str, *, bay_class: str = "Standard", hourly_rate: Decimal = Decimal("4.20"), maintenance_reason=None):
    return ParkingSpot(
        id=spot_id,
        floor_id="floor-test",
        zone_id="zone-test",
        code=code,
        row="north",
        slot_index=0,
        bay_class=bay_class,
        hourly_rate=hourly_rate,
        sensor_note="test",
        maintenance_reason=maintenance_reason,
    )


def _settings() -> FacilitySettings:
    return FacilitySettings(
        id="settings-test",
        facility_id="facility-test",
        hourly_rate=Decimal("4.20"),
        daily_max_rate=Decimal("28.00"),
        grace_period_minutes=15,
        ev_surcharge=Decimal("0.60"),
        high_occupancy_alert=True,
        reservation_overstay_alert=True,
        space_fault_alert=True,
    )


def _settings_view(**overrides) -> FacilitySettingsView:
    values = {
        "facility_id": "facility-test",
        "facility_name": "Test Hub",
        "facility_address": "1 Test Street",
        "operating_hours": "00:00 – 23:59 (24/7)",
        "hourly_rate": Decimal("4.20"),
        "daily_max_rate": Decimal("28.00"),
        "grace_period_minutes": 15,
        "ev_surcharge": Decimal("0.60"),
        "high_occupancy_alert": True,
        "reservation_overstay_alert": True,
        "space_fault_alert": True,
    }
    values.update(overrides)
    return FacilitySettingsView(**values)
