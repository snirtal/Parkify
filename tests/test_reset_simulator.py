"""Selection rules for resetting live-simulator data. These tests do not use a database."""

from repositories.seed import VEHICLES, vehicle_id
from scripts.reset_simulator_data import is_simulator_vehicle

SEED_PLATES = {row[0] for row in VEHICLES}
SEED_IDS = {vehicle_id(plate) for plate in SEED_PLATES}


def _owned(vehicle_id_value: str, plate: str, *, history: bool = True) -> bool:
    return is_simulator_vehicle(
        vehicle_id_value,
        plate,
        seed_plates=SEED_PLATES,
        seed_ids=SEED_IDS,
        has_gate_history=history,
    )


def test_seed_plates_are_kept_even_when_they_have_gate_history():
    for plate in SEED_PLATES:
        assert _owned(vehicle_id(plate), plate) is False


def test_an_lx_prefix_alone_does_not_make_a_vehicle_simulator_data():
    assert _owned("veh-0123456789ab", "LX-ONLY") is False
    assert _owned("veh-0123456789ab", "LXI-100B") is False
    assert _owned("veh-0123456789ab", "LXO-100A") is False
    assert _owned("veh-0123456789ab", "LKS-290A") is False


def test_a_generated_plate_with_a_seed_style_id_is_kept():
    assert _owned("veh-lxk-482m", "LXK-482M") is False


def test_a_generated_plate_without_gate_history_is_kept():
    assert _owned("veh-0123456789ab", "LXK-482M", history=False) is False


def test_a_generated_plate_with_an_api_id_and_gate_history_is_removed():
    assert _owned("veh-0123456789ab", "LXK-482M") is True
