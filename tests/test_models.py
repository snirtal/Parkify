"""ORM shape checks that do not require a database connection."""

from __future__ import annotations

from models.orm import ParkingSession, ParkingSpot, Reservation


def test_parking_spot_does_not_store_occupancy_status() -> None:
    assert "status" not in ParkingSpot.__table__.columns


def test_open_session_is_unique_per_spot() -> None:
    indexes = {index.name: index for index in ParkingSession.__table__.indexes}
    index = indexes["uq_parking_sessions_open_spot"]
    where = index.dialect_options["postgresql"]["where"]
    assert index.unique is True
    assert getattr(where, "text", str(where)) == "ended_at IS NULL"


def test_reservations_exclude_overlapping_windows() -> None:
    names = {constraint.name for constraint in Reservation.__table__.constraints}
    assert "ex_reservations_no_overlap" in names
    assert "ck_reservations_window" in names
