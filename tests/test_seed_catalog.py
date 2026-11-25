"""Seed catalog checks that do not require a database connection."""

from __future__ import annotations

from repositories.seed import (
    ACTIVE_SESSIONS,
    COMPLETED_SESSIONS,
    GATE_LOGS,
    RESERVATIONS,
    SPOTS,
    VEHICLES,
)


def test_seed_catalog_matches_the_frontend_snapshot() -> None:
    codes = [row[1] for row in SPOTS]
    plates = {row[0] for row in VEHICLES}

    assert len(SPOTS) == 24
    assert set(codes) == {f"P-{number}" for number in [*range(201, 213), *range(101, 113)]}
    assert len({row[0] for row in SPOTS}) == 24
    assert len(ACTIVE_SESSIONS) == 14
    assert len(COMPLETED_SESSIONS) == 2
    assert len(RESERVATIONS) == 6
    assert [row[0] for row in RESERVATIONS] == [f"res-{number}" for number in range(1, 7)]
    assert [row[0] for row in GATE_LOGS] == [f"gl-{number}" for number in range(1, 7)]
    assert len(plates) == 22
    assert {row[1] for row in ACTIVE_SESSIONS} <= plates
    assert {row[1] for row in RESERVATIONS} <= plates
    assert {row[2] for row in GATE_LOGS} <= plates
    assert {row[5] for row in GATE_LOGS} <= set(codes)
