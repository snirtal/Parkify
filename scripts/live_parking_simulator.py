"""Send one real gate event every five seconds to the isolated Parkify API.

Each tick advances the facility clock by five minutes, then posts either an
entry or an exit. The API applies the existing occupancy rules. Plates look
like the facility's other plates and always start with LX so they can be
told apart from the seed vehicles.

Start, from the repository root, after the isolated API is listening:

    .venv/bin/python scripts/live_parking_simulator.py

Stop:

    pkill -f scripts/live_parking_simulator.py
"""

from __future__ import annotations

import json
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

from config.config_loader import load_project_env
from config.database import normalize_database_url
from config.facility import configured_facility_id
from scripts.run_isolated_api import isolated_database_url

load_project_env()
FACILITY_ID = configured_facility_id()
API_ROOT = f"http://127.0.0.1:5002/api/facilities/{FACILITY_ID}"
EVENT_INTERVAL_SECONDS = 5
CLOCK_STEP = timedelta(minutes=5)
FLEET_SIZE = 3
PLATE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_plate(rng: random.Random) -> str:
    """Return a plate such as LXK-482M."""
    return f"LX{rng.choice(PLATE_LETTERS)}-{rng.randint(100, 999)}{rng.choice(PLATE_LETTERS)}"


def choose_gate_action(
    available_spots: list[str],
    own_sessions: list[str],
    rng: random.Random,
    *,
    fleet_size: int = FLEET_SIZE,
) -> tuple[str, str] | None:
    """Pick a legal entry or the oldest simulator exit.

    `own_sessions` is oldest first and contains only plates this simulator
    parked. Spots that are occupied, reserved, or offline are not offered.
    """
    if fleet_size < 1:
        raise ValueError("fleet_size must be at least 1")
    if not available_spots and not own_sessions:
        return None
    if not own_sessions:
        return ("entry", rng.choice(available_spots))
    if not available_spots or len(own_sessions) >= fleet_size:
        return ("exit", own_sessions[0])
    return ("entry", rng.choice(available_spots))


def next_facility_moment(current: datetime, step: timedelta = CLOCK_STEP) -> datetime:
    """Move the naive facility clock forward."""
    if current.tzinfo is not None:
        raise ValueError("The facility clock must not include a time zone.")
    if step <= timedelta(0):
        raise ValueError("The facility clock must move forward.")
    return current + step


def advance_facility_clock(connection, facility_id: str, step: timedelta = CLOCK_STEP) -> datetime:
    """Persist the next facility clock. The caller must already be isolated."""
    row = connection.execute(
        text(
            "SELECT simulated_date, simulated_time FROM facilities WHERE id = :id"
        ),
        {"id": facility_id},
    ).one()
    moment = next_facility_moment(datetime.combine(row.simulated_date, row.simulated_time), step)
    connection.execute(
        text(
            """
            UPDATE facilities
            SET simulated_date = :simulated_date,
                simulated_time = :simulated_time,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            """
        ),
        {
            "simulated_date": moment.date(),
            "simulated_time": moment.time().replace(microsecond=0),
            "id": facility_id,
        },
    )
    return moment


def _request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"error": {"message": raw or exc.reason}}
        return exc.code, parsed


def _error_message(payload: dict) -> str:
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    return "The API rejected the gate event."


def _own_sessions(items: list[dict]) -> list[dict]:
    owned = [item for item in items if str(item.get("plate_number", "")).startswith("LX")]
    owned.sort(key=lambda item: item.get("started_at") or "")
    return owned


def run_once(rng: random.Random, engine) -> str:
    """Advance the clock and send one gate event. Returns a one-line result."""
    with engine.begin() as connection:
        moment = advance_facility_clock(connection, FACILITY_ID)
    clock = moment.strftime("%Y-%m-%d %H:%M")

    occupancy_status, occupancy = _request("GET", "/occupancy")
    session_status, sessions = _request("GET", "/sessions")
    if occupancy_status != 200 or session_status != 200:
        return f"{clock} skipped because the facility could not be read"

    available = [
        spot["code"]
        for spot in occupancy.get("spots", [])
        if spot.get("status") == "available"
    ]
    owned = _own_sessions(sessions.get("items", []))
    action = choose_gate_action(available, [item["plate_number"] for item in owned], rng)
    if action is None:
        return f"{clock} no legal entry or exit"

    kind, target = action
    if kind == "entry":
        plates = {item.get("plate_number") for item in sessions.get("items", [])}
        plate = generate_plate(rng)
        while plate in plates:
            plate = generate_plate(rng)
        status, payload = _request(
            "POST",
            "/entries",
            {"plate_number": plate, "spot_code": target},
        )
        if status not in (200, 201):
            return f"{clock} entry {plate} at {target} rejected: {_error_message(payload)}"
        return f"{clock} entry {plate} at {target}"

    status, payload = _request("POST", "/exits", {"plate_number": target})
    if status != 200:
        return f"{clock} exit {target} rejected: {_error_message(payload)}"
    quote = payload.get("quote") or {}
    amount = quote.get("amount")
    duration = quote.get("duration_label") or quote.get("duration")
    detail = f" charge {amount}" if amount else ""
    if duration:
        detail = f"{detail} for {duration}"
    return f"{clock} exit {target}{detail}"


def main() -> None:
    # Touch dotenv keys only to fail fast with the same guard as the API.
    dotenv_values(ROOT / ".env")
    database_url = isolated_database_url()
    engine = create_engine(normalize_database_url(database_url))
    rng = random.Random()
    print(
        "Live simulator posting to http://127.0.0.1:5002 every 5s; "
        "facility clock moves 5 minutes per event",
        flush=True,
    )
    try:
        while True:
            try:
                print(run_once(rng, engine), flush=True)
            except Exception as exc:
                print(f"tick failed: {type(exc).__name__}", flush=True)
            time.sleep(EVENT_INTERVAL_SECONDS)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
