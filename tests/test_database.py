"""Database integration tests.

These tests use only TEST_DATABASE_URL. They are skipped until that variable
points at an isolated Neon branch. They never connect to DATABASE_URL and
they roll back every row they insert.
"""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from config.database import normalize_database_url
from repositories.seed import CLOCK, seed_database

load_dotenv()

_PLACEHOLDERS = ("USER:PASSWORD", "ep-example")


def _raw(name: str) -> str:
    return os.getenv(name, "").strip()


def _usable_test_url() -> str:
    raw = _raw("TEST_DATABASE_URL")
    if not raw or any(marker in raw for marker in _PLACEHOLDERS):
        pytest.skip(
            "SKIPPED: TEST_DATABASE_URL is not configured. Create an isolated "
            "Neon branch and set TEST_DATABASE_URL before running database "
            "integration tests."
        )
    test_url = normalize_database_url(raw)
    primary = normalize_database_url(_raw("DATABASE_URL"))
    migration = normalize_database_url(_raw("MIGRATION_DATABASE_URL"))
    if test_url in {primary, migration} - {""}:
        pytest.skip(
            "SKIPPED: TEST_DATABASE_URL matches the primary database. "
            "Use a separate Neon branch so tests cannot change primary data."
        )
    return test_url


@pytest.fixture(scope="module")
def migrated_engine():
    """Apply migrations to the isolated test branch. Never drops data."""
    url = _usable_test_url()
    os.environ["MIGRATION_DATABASE_URL"] = url
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(url, poolclass=NullPool, future=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(migrated_engine):
    """A transaction that is always rolled back, including seed commits."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_database_connection(migrated_engine) -> None:
    with migrated_engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_seed_preserves_layout_and_is_idempotent(db_session: Session) -> None:
    first = seed_database(db_session)
    second = seed_database(db_session)
    assert first == second
    assert first["spots"] == 24
    assert first["floors"] == 2
    assert first["zones"] == 4
    assert first["sessions"] == 16
    assert first["reservations"] == 6
    assert first["gate_activities"] == 6
    assert first["vehicles"] == 22

    from models.orm import ParkingSpot

    codes = set(db_session.scalars(select(ParkingSpot.code)))
    assert codes == {f"P-{number}" for number in list(range(201, 213)) + list(range(101, 113))}


def test_seed_relationships(db_session: Session) -> None:
    seed_database(db_session)
    from models.orm import GateActivity, ParkingSpot

    spot = db_session.get(ParkingSpot, "bay-p204")
    assert spot is not None
    assert spot.code == "P-204"
    assert spot.zone.code == "P2-N"
    assert spot.floor.code == "P2"
    open_sessions = [item for item in spot.sessions if item.ended_at is None]
    assert len(open_sessions) == 1
    assert open_sessions[0].vehicle.plate_number == "VEL-204X"
    assert open_sessions[0].has_alert is True

    gate = db_session.get(GateActivity, "gl-5")
    assert gate is not None
    assert gate.reservation_id == "res-1"
    assert gate.reservation is not None
    assert gate.reservation.spot.code == "P-203"
    assert gate.vehicle.driver_name == "Elena Rostova"


def test_derived_occupancy_matches_the_frontend_snapshot(db_session: Session) -> None:
    seed_database(db_session)
    from models.orm import ParkingSession, ParkingSpot, Reservation

    spots = list(db_session.scalars(select(ParkingSpot)))
    occupied = 0
    unavailable = 0
    reserved = 0
    available = 0
    for spot in spots:
        has_open_session = any(item.ended_at is None for item in spot.sessions)
        if has_open_session:
            occupied += 1
            continue
        if spot.maintenance_reason:
            unavailable += 1
            continue
        has_hold = any(
            item.status != "Cancelled" and item.starts_at <= CLOCK < item.ends_at
            for item in spot.reservations
        )
        if has_hold:
            reserved += 1
        else:
            available += 1

    assert (occupied, reserved, unavailable, available) == (14, 2, 2, 6)
    from sqlalchemy import func

    completed = db_session.scalar(
        select(func.count())
        .select_from(ParkingSession)
        .where(ParkingSession.status == "Completed")
    )
    assert completed == 2


def test_duplicate_spot_code_is_rejected(db_session: Session) -> None:
    seed_database(db_session)
    from models.orm import ParkingSpot

    db_session.add(
        ParkingSpot(
            id="bay-duplicate",
            floor_id="floor-p2",
            zone_id="z-p2n",
            code="P-201",
            row="north",
            slot_index=9,
            bay_class="Standard",
            hourly_rate="4.20",
            sensor_note="duplicate",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_second_open_session_on_a_spot_is_rejected(db_session: Session) -> None:
    seed_database(db_session)
    from datetime import datetime

    from models.orm import ParkingSession

    db_session.add(
        ParkingSession(
            id="ses-conflict",
            spot_id="bay-p204",
            vehicle_id="veh-chi-901a",
            status="Active",
            started_at=datetime(2026, 11, 25, 15, 0, 0),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_overlapping_reservation_is_rejected(db_session: Session) -> None:
    seed_database(db_session)
    from datetime import datetime

    from models.orm import Reservation

    db_session.add(
        Reservation(
            id="res-overlap",
            spot_id="bay-p203",
            vehicle_id="veh-exec-104",
            status="Scheduled",
            starts_at=datetime(2026, 11, 25, 16, 0, 0),
            ends_at=datetime(2026, 11, 25, 17, 0, 0),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
