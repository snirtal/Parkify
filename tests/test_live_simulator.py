"""Decision rules for the live parking simulator. These tests do not use a database."""

from datetime import datetime, timedelta, timezone
from random import Random

import pytest

from scripts.live_parking_simulator import (
    choose_gate_action,
    generate_plate,
    next_facility_moment,
)
from scripts.run_isolated_api import isolated_database_url
from tests.db_safety import database_identity


def test_plates_look_like_facility_plates_and_stay_unique():
    rng = Random(7)
    plates = {generate_plate(rng) for _ in range(40)}
    assert len(plates) == 40
    for plate in plates:
        assert plate.startswith("LX")
        assert 2 <= len(plate) <= 16
        assert plate[3] == "-"


def test_entry_uses_only_an_available_spot():
    action = choose_gate_action(["P-210", "P-202"], [], Random(1))
    assert action is not None
    assert action[0] == "entry"
    assert action[1] in {"P-210", "P-202"}


def test_exit_uses_the_oldest_simulator_session_when_the_lot_is_full():
    action = choose_gate_action([], ["LXA-100B", "LXC-200D"], Random(1))
    assert action == ("exit", "LXA-100B")


def test_fleet_exits_once_three_simulator_vehicles_are_parked():
    parked = ["LXA-100B", "LXC-200D", "LXE-300F"]
    action = choose_gate_action(["P-101"], parked, Random(1))
    assert action == ("exit", "LXA-100B")


def test_fleet_enters_while_there_is_room_and_an_open_stall():
    action = choose_gate_action(["P-108"], ["LXA-100B"], Random(1))
    assert action == ("entry", "P-108")


def test_no_event_when_nothing_can_enter_or_leave():
    assert choose_gate_action([], [], Random(1)) is None


def test_facility_clock_moves_forward_by_five_minutes():
    moment = next_facility_moment(datetime(2026, 11, 25, 14, 24))
    assert moment == datetime(2026, 11, 25, 14, 29)


def test_facility_clock_rejects_a_time_zone_and_a_backward_step():
    with pytest.raises(ValueError):
        next_facility_moment(datetime(2026, 11, 25, 14, 24, tzinfo=timezone.utc))
    with pytest.raises(ValueError):
        next_facility_moment(datetime(2026, 11, 25, 14, 24), step=timedelta(0))


def test_isolated_api_refuses_the_primary_database(monkeypatch):
    primary = "postgresql://user:secret@ep-primary.neon.tech/parkify"
    monkeypatch.setattr(
        "scripts.run_isolated_api.dotenv_values",
        lambda _path: {
            "TEST_DATABASE_URL": primary,
            "DATABASE_URL": primary,
            "MIGRATION_DATABASE_URL": "postgresql://user:secret@ep-migrate.neon.tech/parkify",
        },
    )
    with pytest.raises(SystemExit):
        isolated_database_url()
    assert database_identity(primary)[0].startswith("ep-primary")
