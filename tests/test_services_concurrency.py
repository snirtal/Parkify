"""Two real connections compete for one spot on the isolated test branch.

The rows use ids that belong only to this test. They are removed afterward.
Production data is not used.
"""

from __future__ import annotations

import threading
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.orm import Facility, Floor, ParkingSpot, ParkingZone, Reservation, Vehicle
from services.exceptions import ConflictError
from services.factory import build_services
from services.support import FixedClock, default_id
from services.unit_of_work import SqlAlchemyUnitOfWork

FACILITY_ID = "facility-svc-conc"
FLOOR_ID = "floor-svc-conc"
ZONE_ID = "zone-svc-conc"
SPOT_ID = "spot-svc-conc"
SPOT_B_ID = "spot-svc-conc-b"
CLOCK = datetime(2026, 11, 25, 14, 24)
PLATES = ("CONC-1", "CONC-2", "CONC-3")


def test_concurrent_entries_for_one_spot_allow_only_one_session(migrated_engine) -> None:
    _cleanup(migrated_engine)
    _setup(migrated_engine)
    try:
        results = _race(
            migrated_engine,
            [
                lambda services: services.sessions.start_session(FACILITY_ID, "CONC-1", "T-001"),
                lambda services: services.sessions.start_session(FACILITY_ID, "CONC-1", "T-001"),
            ],
        )
        assert sorted(results) == ["conflict", "ok"]
    finally:
        _cleanup(migrated_engine)


def test_concurrent_reservation_creates_for_one_spot_allow_one(migrated_engine) -> None:
    _cleanup(migrated_engine)
    _setup(migrated_engine)
    window = (datetime(2026, 11, 26, 9, 0), datetime(2026, 11, 26, 11, 0))
    try:
        results = _race(
            migrated_engine,
            [
                lambda services: services.reservations.create_reservation(
                    FACILITY_ID, "CONC-1", "T-001", *window
                ),
                lambda services: services.reservations.create_reservation(
                    FACILITY_ID, "CONC-2", "T-001", *window
                ),
            ],
        )
        assert sorted(results) == ["conflict", "ok"]
    finally:
        _cleanup(migrated_engine)


def test_concurrent_reservation_creates_for_one_vehicle_allow_one(migrated_engine) -> None:
    _cleanup(migrated_engine)
    _setup(migrated_engine)
    window = (datetime(2026, 11, 26, 9, 0), datetime(2026, 11, 26, 11, 0))
    try:
        results = _race(
            migrated_engine,
            [
                lambda services: services.reservations.create_reservation(
                    FACILITY_ID, "CONC-1", "T-001", *window
                ),
                lambda services: services.reservations.create_reservation(
                    FACILITY_ID, "CONC-1", "T-002", *window
                ),
            ],
        )
        assert sorted(results) == ["conflict", "ok"]
    finally:
        _cleanup(migrated_engine)


def test_concurrent_reservation_updates_for_one_vehicle_allow_one(migrated_engine) -> None:
    _cleanup(migrated_engine)
    _setup(migrated_engine)
    _seed_update_pair(migrated_engine, same_vehicle=True)
    new_window = {
        "starts_at": datetime(2026, 11, 26, 11, 0),
        "ends_at": datetime(2026, 11, 26, 12, 0),
    }
    try:
        results = _race(
            migrated_engine,
            [
                lambda services: services.reservations.update_reservation(
                    FACILITY_ID, "res-svc-conc-a", **new_window
                ),
                lambda services: services.reservations.update_reservation(
                    FACILITY_ID, "res-svc-conc-b", **new_window
                ),
            ],
        )
        assert sorted(results) == ["conflict", "ok"]
    finally:
        _cleanup(migrated_engine)


def test_concurrent_reservation_updates_for_one_spot_allow_one(migrated_engine) -> None:
    _cleanup(migrated_engine)
    _setup(migrated_engine)
    _seed_update_pair(migrated_engine, same_vehicle=False)
    move = {
        "spot_code": "T-001",
        "starts_at": datetime(2026, 11, 26, 11, 0),
        "ends_at": datetime(2026, 11, 26, 12, 0),
    }
    try:
        results = _race(
            migrated_engine,
            [
                lambda services: services.reservations.update_reservation(
                    FACILITY_ID, "res-svc-conc-a", **move
                ),
                lambda services: services.reservations.update_reservation(
                    FACILITY_ID, "res-svc-conc-b", **move
                ),
            ],
        )
        assert sorted(results) == ["conflict", "ok"]
    finally:
        _cleanup(migrated_engine)


def _race(engine, operations) -> list[str]:
    results: list[str] = []
    barrier = threading.Barrier(len(operations))

    def attempt(operation) -> None:
        session = Session(bind=engine, autoflush=False, expire_on_commit=False)
        services = build_services(
            lambda: SqlAlchemyUnitOfWork(
                session,
                close_session=True,
                lock_timeout_ms=15000,
            ),
            clock=FixedClock(CLOCK),
            ids=default_id,
        )
        try:
            barrier.wait(20)
            operation(services)
            results.append("ok")
        except ConflictError:
            results.append("conflict")
        except Exception as exc:
            results.append(type(exc).__name__)

    threads = [threading.Thread(target=attempt, args=(operation,)) for operation in operations]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(40)
    return results


def _setup(engine) -> None:
    session = Session(bind=engine, autoflush=False, expire_on_commit=False)
    session.add(
        Facility(
            id=FACILITY_ID,
            name="Concurrency Test",
            address="1 Isolated Way",
            operating_hours="24/7",
            simulated_date=date(2026, 11, 25),
            simulated_time=time(14, 24),
            snapshot_label="concurrency",
        )
    )
    session.add(
        Floor(
            id=FLOOR_ID,
            facility_id=FACILITY_ID,
            code="T9",
            name="Concurrency deck",
            level_index=9,
        )
    )
    session.add(
        ParkingZone(
            id=ZONE_ID,
            floor_id=FLOOR_ID,
            code="T-SVC",
            name="Concurrency zone",
            category="Test",
            dashboard_category="Standard",
            accent="blue",
        )
    )
    session.add(_spot(SPOT_ID, "T-001", 0))
    session.add(_spot(SPOT_B_ID, "T-002", 1))
    session.commit()
    session.close()


def _spot(spot_id: str, code: str, slot_index: int) -> ParkingSpot:
    return ParkingSpot(
        id=spot_id,
        floor_id=FLOOR_ID,
        zone_id=ZONE_ID,
        code=code,
        row="north",
        slot_index=slot_index,
        bay_class="Standard",
        hourly_rate=Decimal("4.20"),
        sensor_note="concurrency",
    )


def _seed_update_pair(engine, *, same_vehicle: bool) -> None:
    """Commit two non-overlapping reservations the update races then move together."""
    session = Session(bind=engine, autoflush=False, expire_on_commit=False)
    session.add(Vehicle(id="veh-svc-conc-a", plate_number="CONC-2"))
    second_vehicle_id = "veh-svc-conc-a"
    if not same_vehicle:
        session.add(Vehicle(id="veh-svc-conc-b", plate_number="CONC-3"))
        second_vehicle_id = "veh-svc-conc-b"
    session.add(
        Reservation(
            id="res-svc-conc-a",
            spot_id=SPOT_B_ID,
            vehicle_id="veh-svc-conc-a",
            status="Scheduled",
            starts_at=datetime(2026, 11, 26, 9, 0),
            ends_at=datetime(2026, 11, 26, 10, 0),
            is_seeded=False,
        )
    )
    session.add(
        Reservation(
            id="res-svc-conc-b",
            spot_id=SPOT_ID,
            vehicle_id=second_vehicle_id,
            status="Scheduled",
            starts_at=datetime(2026, 11, 26, 15, 0),
            ends_at=datetime(2026, 11, 26, 16, 0),
            is_seeded=False,
        )
    )
    session.commit()
    session.close()


def _cleanup(engine) -> None:
    plates = ", ".join(f"'{plate}'" for plate in PLATES)
    spot_ids = f"'{SPOT_ID}', '{SPOT_B_ID}'"
    vehicle_ids = (
        f"SELECT id FROM vehicles WHERE plate_number IN ({plates})"
    )
    statements = (
        f"DELETE FROM gate_activities WHERE spot_id IN ({spot_ids}) OR vehicle_id IN ({vehicle_ids})",
        f"DELETE FROM parking_sessions WHERE spot_id IN ({spot_ids}) OR vehicle_id IN ({vehicle_ids})",
        f"DELETE FROM reservations WHERE spot_id IN ({spot_ids}) OR vehicle_id IN ({vehicle_ids})",
        f"DELETE FROM parking_spots WHERE id IN ({spot_ids})",
        "DELETE FROM parking_zones WHERE id = 'zone-svc-conc'",
        "DELETE FROM floors WHERE id = 'floor-svc-conc'",
        "DELETE FROM facility_settings WHERE facility_id = 'facility-svc-conc'",
        f"DELETE FROM vehicles WHERE plate_number IN ({plates})",
        "DELETE FROM facilities WHERE id = 'facility-svc-conc'",
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
