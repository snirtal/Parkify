"""Delete live-simulator rows from the isolated test database only.

A vehicle is removed only when its plate matches the simulator generator, it
is not part of the seed catalog, its id was issued by the API, and it has a
parking session or gate event. Seed spots, floors, zones, pricing, settings,
and the facility row are not changed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import bindparam, create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.database import normalize_database_url
from repositories.seed import VEHICLES, vehicle_id
from scripts.live_parking_simulator import PLATE_LETTERS
from scripts.run_isolated_api import isolated_database_url
from tests.db_safety import database_identity

SIMULATOR_PLATE = re.compile(rf"^LX[{PLATE_LETTERS}]-[0-9]{{3}}[{PLATE_LETTERS}]$")
API_VEHICLE_ID = re.compile(r"^veh-[0-9a-f]{12}$")


def is_simulator_vehicle(
    vehicle_id_value: str,
    plate: str,
    *,
    seed_plates: set[str],
    seed_ids: set[str],
    has_gate_history: bool,
) -> bool:
    """Return whether this vehicle was created by the live simulator."""
    if plate in seed_plates or vehicle_id_value in seed_ids:
        return False
    if vehicle_id_value == vehicle_id(plate):
        return False
    if not SIMULATOR_PLATE.fullmatch(plate):
        return False
    if not API_VEHICLE_ID.fullmatch(vehicle_id_value):
        return False
    return has_gate_history


def _seed_catalog() -> tuple[set[str], set[str]]:
    plates = {row[0] for row in VEHICLES}
    return plates, {vehicle_id(plate) for plate in plates}


def select_simulator_ids(connection) -> list[str]:
    seed_plates, seed_ids = _seed_catalog()
    rows = connection.execute(
        text(
            """
            SELECT v.id,
                   v.plate_number,
                   (
                       EXISTS (SELECT 1 FROM parking_sessions s WHERE s.vehicle_id = v.id)
                       OR EXISTS (SELECT 1 FROM gate_activities g WHERE g.vehicle_id = v.id)
                   ) AS has_gate_history
            FROM vehicles v
            ORDER BY v.plate_number
            """
        )
    ).all()
    chosen = [
        row.id
        for row in rows
        if is_simulator_vehicle(
            row.id,
            row.plate_number,
            seed_plates=seed_plates,
            seed_ids=seed_ids,
            has_gate_history=bool(row.has_gate_history),
        )
    ]
    if set(chosen) & seed_ids:
        raise SystemExit("Refusing to delete: a seed vehicle was selected.")
    return chosen


def _expanding(statement: str):
    return text(statement).bindparams(bindparam("ids", expanding=True))


def _delete_count(connection, statement: str, ids: list[str]) -> int:
    result = connection.execute(_expanding(statement), {"ids": ids})
    return len(result.all())


def delete_simulator_records(connection, ids: list[str]) -> dict[str, int]:
    """Delete one simulator fleet inside the caller's transaction."""
    seed_plates, seed_ids = _seed_catalog()
    if set(ids) & seed_ids:
        raise SystemExit("Refusing to delete: a seed vehicle was selected.")
    plates = connection.execute(
        _expanding("SELECT plate_number FROM vehicles WHERE id IN :ids"),
        {"ids": ids},
    ).scalars().all()
    if any(plate in seed_plates or not SIMULATOR_PLATE.fullmatch(plate) for plate in plates):
        raise SystemExit("Refusing to delete: the selection is not simulator data.")
    if len(plates) != len(ids):
        raise SystemExit("Refusing to delete: a selected vehicle is no longer present.")

    connection.execute(
        _expanding("SELECT id FROM vehicles WHERE id IN :ids FOR UPDATE"),
        {"ids": ids},
    ).all()
    gate_events = _delete_count(
        connection,
        """
        DELETE FROM gate_activities
        WHERE reservation_id IN (
            SELECT id FROM reservations WHERE vehicle_id IN :ids
        )
        RETURNING id
        """,
        ids,
    )
    gate_events += _delete_count(
        connection,
        "DELETE FROM gate_activities WHERE vehicle_id IN :ids RETURNING id",
        ids,
    )
    sessions = _delete_count(
        connection,
        "DELETE FROM parking_sessions WHERE vehicle_id IN :ids RETURNING id",
        ids,
    )
    reservations = _delete_count(
        connection,
        "DELETE FROM reservations WHERE vehicle_id IN :ids RETURNING id",
        ids,
    )
    vehicles = _delete_count(
        connection,
        "DELETE FROM vehicles WHERE id IN :ids RETURNING id",
        ids,
    )
    return {
        "vehicles": vehicles,
        "sessions": sessions,
        "gate_activities": gate_events,
        "reservations": reservations,
    }


def _assert_isolated(url: str) -> None:
    identity = database_identity(url)
    if not identity[0] or identity[1] in {"", "/"}:
        raise SystemExit("Refusing to reset: the test database identity is incomplete.")
    values = dotenv_values(ROOT / ".env")
    for label, key in (("primary", "DATABASE_URL"), ("migration", "MIGRATION_DATABASE_URL")):
        other = (values.get(key) or "").strip()
        if other and database_identity(other) == identity:
            raise SystemExit(f"Refusing to reset: the test database is the {label} database.")


def _confirm(ids: list[str]) -> bool:
    print(
        f"This will delete {len(ids)} simulator vehicles and their sessions, "
        "gate activity, and reservations from the isolated test database."
    )
    print("Type yes to continue.")
    try:
        answer = input().strip().lower()
    except EOFError:
        answer = ""
    return answer == "yes"


def _print_summary(deleted: dict[str, int]) -> None:
    print("Deleted simulator records:")
    for name in ("vehicles", "sessions", "gate_activities", "reservations"):
        print(f"  {name}: {deleted[name]}")


def main() -> None:
    url = isolated_database_url()
    _assert_isolated(url)
    engine = create_engine(normalize_database_url(url), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            ids = select_simulator_ids(connection)
        if not ids:
            print("No simulator records to delete.")
            return
        if not _confirm(ids):
            print("Reset cancelled. No records were deleted.")
            return
        with engine.begin() as connection:
            ids = select_simulator_ids(connection)
            if not ids:
                print("No simulator records to delete.")
                return
            deleted = delete_simulator_records(connection, ids)
    finally:
        engine.dispose()
    _print_summary(deleted)
    print("Seed data was left in place. The simulator was not started.")


if __name__ == "__main__":
    main()
