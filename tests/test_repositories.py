"""Repository integration tests against the isolated Neon branch.

Every write stays inside the rolled-back test transaction.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.orm import Vehicle
from repositories.factory import build_repositories
from repositories.seed import seed_database


def test_repository_queries_match_the_seeded_snapshot(db_session: Session) -> None:
    seed_database(db_session)
    repos = build_repositories(db_session)

    facility = repos.facilities.get_with_children("facility-skyline")
    assert facility is not None
    assert facility.settings.hourly_rate == Decimal("4.20")
    floors = sorted(facility.floors, key=lambda floor: floor.level_index)
    assert [floor.code for floor in floors] == ["P1", "P2"]
    assert {zone.code for floor in facility.floors for zone in floor.zones} == {
        "P1-N",
        "P1-S",
        "P2-N",
        "P2-S",
    }

    assert len(repos.spots.list_for_floor("floor-p2")) == 12
    assert [spot.code for spot in repos.spots.list_for_zone("z-p2n")] == [
        "P-201",
        "P-202",
        "P-203",
        "P-204",
        "P-205",
        "P-206",
    ]
    spot = repos.spots.get_by_code("P-204")
    assert spot is not None
    assert spot.zone.code == "P2-N"
    assert "status" not in spot.__table__.columns

    vehicle = repos.vehicles.get_by_plate("VEL-204X")
    assert vehicle is not None
    active = repos.sessions.list_active()
    assert len(active) == 14
    open_session = repos.sessions.get_active_for_spot("bay-p204")
    assert open_session is not None
    assert open_session.vehicle.plate_number == "VEL-204X"
    assert any(item.id == open_session.id for item in repos.sessions.list_for_vehicle(vehicle.id))
    assert len(repos.sessions.list_for_spot("bay-p202")) == 1
    assert repos.sessions.list_for_spot("bay-p202")[0].status == "Completed"

    active_reservations = repos.reservations.list_filtered(status="Active")
    assert {item.id for item in active_reservations} == {"res-1", "res-2"}
    overlap = repos.reservations.list_overlapping(
        "bay-p203",
        datetime(2026, 11, 25, 16, 0),
        datetime(2026, 11, 25, 17, 0),
    )
    assert [item.id for item in overlap] == ["res-1"]
    next_day = repos.reservations.list_filtered(
        range_start=datetime(2026, 11, 26, 0, 0),
        range_end=datetime(2026, 11, 27, 0, 0),
    )
    assert {item.id for item in next_day} == {"res-3", "res-4"}
    cancelled = repos.reservations.list_filtered(status="Cancelled", spot_id="bay-p109")
    assert [item.id for item in cancelled] == ["res-6"]

    page = repos.gate_activities.list_page(limit=2, offset=0)
    assert page.total == 6
    assert [item.id for item in page.items] == ["gl-1", "gl-2"]
    assert page.items[0].vehicle.plate_number == "VEL-204X"
    entries = repos.gate_activities.list_page(direction="entry", limit=10)
    assert entries.total == 4


def test_settings_changes_stay_on_the_pending_object(db_session: Session) -> None:
    seed_database(db_session)
    repos = build_repositories(db_session)
    settings = repos.settings.get_for_facility("facility-skyline")
    assert settings is not None
    repos.settings.apply_changes(settings, grace_period_minutes=20)
    assert settings.grace_period_minutes == 20
    assert db_session.get_transaction() is not None


def test_repository_writes_are_not_visible_to_other_connections(
    db_session: Session, migrated_engine
) -> None:
    repos = build_repositories(db_session)
    repos.vehicles.add(Vehicle(id="veh-repo-temp", plate_number="REPO-TEMP"))
    db_session.flush()
    with migrated_engine.connect() as other:
        found = other.execute(
            text("SELECT id FROM vehicles WHERE id = 'veh-repo-temp'")
        ).first()
    assert found is None
