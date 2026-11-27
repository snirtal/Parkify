"""Send one real gate event every five seconds to the isolated Parkify API.

Each tick advances the facility clock by five minutes, then posts either an
entry or an exit. The API applies the existing occupancy rules. Plates look
like the facility's other plates and always start with LX so they can be
told apart from the seed vehicles.

Start, from the repository root, after the isolated API is listening:

    .venv/bin/python scripts/live_parking_simulator.py

Stop:

    pkill -f scripts/live_parking_simulator.py

Business endpoints now require an operator session. This simulator does not
sign in and does not contain credentials. Occupancy reads and gate posts
receive 401 until a later phase adds a simulator identity.
"""

from __future__ import annotations

import json
import logging
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
from config.settings import get_settings
from scripts.run_isolated_api import isolated_database_url
from utils.logging_setup import setup_logging

logger = logging.getLogger("parkify.simulator")

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


def _error_code(payload: dict) -> str:
    error = payload.get("error")
    if isinstance(error, dict) and error.get("code"):
        return str(error["code"])
    return "rejected"


def summarize_tick(
    clock: str,
    outcome: str,
    *,
    spot: str | None = None,
    status: int | None = None,
    code: str | None = None,
    charge: str | None = None,
    duration: str | None = None,
) -> str:
    """One simulator log line. License plates are intentionally omitted."""
    detail = f"clock={clock} outcome={outcome}"
    if spot:
        detail = f"{detail} spot={spot}"
    if status is not None:
        detail = f"{detail} status={status}"
    if code:
        detail = f"{detail} code={code}"
    if charge:
        detail = f"{detail} charge={charge}"
    if duration:
        detail = f"{detail} duration={duration}"
    return detail


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
        return summarize_tick(clock, "skipped", status=occupancy_status if occupancy_status != 200 else session_status)

    available = [
        spot["code"]
        for spot in occupancy.get("spots", [])
        if spot.get("status") == "available"
    ]
    owned = _own_sessions(sessions.get("items", []))
    action = choose_gate_action(available, [item["plate_number"] for item in owned], rng)
    if action is None:
        return summarize_tick(clock, "idle")

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
            return summarize_tick(
                clock,
                "entry_rejected",
                spot=target,
                status=status,
                code=_error_code(payload),
            )
        return summarize_tick(clock, "entry", spot=target, status=status)

    status, payload = _request("POST", "/exits", {"plate_number": target})
    if status != 200:
        return summarize_tick(clock, "exit_rejected", status=status, code=_error_code(payload))
    quote = payload.get("quote") or {}
    amount = quote.get("amount")
    duration = quote.get("duration_label") or quote.get("duration")
    return summarize_tick(
        clock,
        "exit",
        status=status,
        charge=None if amount is None else str(amount),
        duration=None if duration is None else str(duration),
    )


def main() -> None:
    # Touch dotenv keys only to fail fast with the same guard as the API.
    dotenv_values(ROOT / ".env")
    setup_logging(get_settings())
    database_url = isolated_database_url()
    engine = create_engine(normalize_database_url(database_url))
    rng = random.Random()
    logger.info(
        "simulator started facility=%s interval_seconds=%s clock_step_minutes=%s",
        FACILITY_ID,
        EVENT_INTERVAL_SECONDS,
        int(CLOCK_STEP.total_seconds() // 60),
    )
    try:
        while True:
            try:
                logger.info(run_once(rng, engine))
            except Exception as exc:
                logger.error("simulator tick failed error=%s", type(exc).__name__)
            time.sleep(EVENT_INTERVAL_SECONDS)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
