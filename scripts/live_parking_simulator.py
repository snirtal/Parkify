"""Send gate events and customer reservation requests to the isolated Parkify API.

The simulator signs in as its own service account. Credentials come from
SIMULATOR_EMAIL and SIMULATOR_PASSWORD. It does not use an admin account,
store a secret in this file, or share a browser session.

Start, from the repository root, after the isolated API is listening and the
simulator user exists:

    .venv/bin/python scripts/live_parking_simulator.py
"""

from __future__ import annotations

import http.cookiejar
import json
import logging
import os
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
from services.rules import BAY_CLASSES
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


def parse_facility_time(value: str) -> datetime:
    """Read a facility-local timestamp from the API."""
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")


def reservation_action(
    reservations: list[dict],
    sessions: list[dict],
    moment: datetime,
) -> tuple[str, str, str | None] | None:
    """Arrive or leave an approved reservation. Pending rows are ignored."""
    open_plates = {item.get("plate_number") for item in sessions}
    open_spots = {item.get("spot_code") for item in sessions}
    arrivals: list[tuple[str, str]] = []
    departures: list[str] = []
    for item in reservations:
        status = item.get("effective_status")
        if status not in {"Active", "Scheduled", "Completed"}:
            continue
        try:
            start = parse_facility_time(str(item["starts_at"]))
            end = parse_facility_time(str(item["ends_at"]))
        except (KeyError, TypeError, ValueError):
            continue
        plate = item.get("plate_number")
        spot = item.get("spot_code")
        if not isinstance(plate, str) or not isinstance(spot, str):
            continue
        if start <= moment < end and status in {"Active", "Scheduled"}:
            if plate not in open_plates and spot not in open_spots:
                arrivals.append((plate, spot))
        elif moment >= end and plate in open_plates:
            departures.append(plate)
    if arrivals:
        plate, spot = arrivals[0]
        return ("entry", plate, spot)
    if departures:
        return ("exit", departures[0], None)
    return None


def plates_inside_reservation(reservations: list[dict], moment: datetime) -> set[str]:
    """Plates whose approved window covers the facility clock."""
    plates: set[str] = set()
    for item in reservations:
        if item.get("effective_status") not in {"Active", "Scheduled"}:
            continue
        try:
            start = parse_facility_time(str(item["starts_at"]))
            end = parse_facility_time(str(item["ends_at"]))
        except (KeyError, TypeError, ValueError):
            continue
        plate = item.get("plate_number")
        if isinstance(plate, str) and start <= moment < end:
            plates.add(plate)
    return plates


def simulator_credentials() -> tuple[str, str]:
    """Read the service account from the environment. Values are not logged."""
    email = os.getenv("SIMULATOR_EMAIL", "").strip()
    password = os.getenv("SIMULATOR_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Simulator credentials are not configured.")
    return email, password


def request_every_ticks() -> int:
    raw = os.getenv("SIMULATOR_REQUEST_EVERY_TICKS", "4").strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit("SIMULATOR_REQUEST_EVERY_TICKS must be a positive integer.") from exc
    if value < 1:
        raise SystemExit("SIMULATOR_REQUEST_EVERY_TICKS must be a positive integer.")
    return value


class SimulatorClient:
    """One machine session. Cookies stay in this process, not in a browser."""

    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._password = password
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._jar))

    def login(self) -> bool:
        status, payload = self._open(
            "POST",
            "http://127.0.0.1:5002/api/auth/login",
            {"email": self._email, "password": self._password},
        )
        if status == 200 and self._csrf():
            logger.info("simulator authenticated")
            return True
        logger.info("simulator sign-in failed status=%s code=%s", status, _error_code(payload))
        return False

    def request(self, method: str, path: str, payload: dict | None = None, *, retry: bool = True):
        status, body = self._open(method, f"{API_ROOT}{path}", payload)
        if status == 401 and retry and self.login():
            return self.request(method, path, payload, retry=False)
        return status, body

    def _csrf(self) -> str:
        for cookie in self._jar:
            if cookie.name == "parkify_csrf":
                return cookie.value
        return ""

    def _open(self, method: str, url: str, payload: dict | None) -> tuple[int, dict]:
        data = None if payload is None else json.dumps(payload).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if method not in {"GET", "HEAD"}:
            token = self._csrf()
            if token:
                headers["X-CSRF-Token"] = token
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self._opener.open(request, timeout=20) as response:
                raw = response.read().decode()
                return response.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"error": {"message": exc.reason}}
            return exc.code, parsed


def next_facility_moment(current: datetime, step: timedelta = CLOCK_STEP) -> datetime:
    """Move the naive facility clock forward."""
    if current.tzinfo is not None:
        raise ValueError("The facility clock must not include a time zone.")
    if step <= timedelta(0):
        raise ValueError("The facility clock must move forward.")
    return current + step


def _error_code(payload: dict) -> str:
    error = payload.get("error")
    if isinstance(error, dict) and error.get("code"):
        return str(error["code"])
    return "rejected"


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


def _maybe_request(rng: random.Random, client: SimulatorClient, moment: datetime) -> None:
    plate = generate_plate(rng)
    bay_class = rng.choice(sorted(BAY_CLASSES))
    start = moment + timedelta(minutes=rng.randint(30, 120))
    duration = rng.choice((60, 90, 120, 180))
    status, payload = client.request(
        "POST",
        "/reservation-requests",
        {
            "plate_number": plate,
            "bay_class": bay_class,
            "starts_at": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "duration_minutes": duration,
        },
    )
    if status == 201:
        logger.info("reservation request created bay_class=%s", bay_class)
        return
    logger.info(
        "reservation request skipped status=%s code=%s",
        status,
        _error_code(payload),
    )


def run_once(
    rng: random.Random,
    engine,
    client: SimulatorClient,
    *,
    tick: int,
    request_every: int,
) -> str:
    """Advance the clock, maybe request a bay, then send one gate event."""
    with engine.begin() as connection:
        moment = advance_facility_clock(connection, FACILITY_ID)
    clock = moment.strftime("%Y-%m-%d %H:%M")
    if tick % request_every == 0:
        _maybe_request(rng, client, moment)

    occupancy_status, occupancy = client.request("GET", "/occupancy")
    session_status, sessions = client.request("GET", "/sessions")
    reservation_status, reservations = client.request("GET", "/reservations")
    if occupancy_status != 200 or session_status != 200 or reservation_status != 200:
        failed = occupancy_status if occupancy_status != 200 else session_status
        if failed == 200:
            failed = reservation_status
        return summarize_tick(clock, "skipped", status=failed)

    session_items = sessions.get("items", [])
    reservation_items = reservations.get("items", [])
    reserved = reservation_action(reservation_items, session_items, moment)
    if reserved is not None:
        kind, plate, spot = reserved
        if kind == "entry" and spot is not None:
            status, payload = client.request(
                "POST",
                "/entries",
                {"plate_number": plate, "spot_code": spot},
            )
            if status not in (200, 201):
                return summarize_tick(
                    clock,
                    "arrival_rejected",
                    spot=spot,
                    status=status,
                    code=_error_code(payload),
                )
            return summarize_tick(clock, "arrival", spot=spot, status=status)
        status, payload = client.request("POST", "/exits", {"plate_number": plate})
        if status != 200:
            return summarize_tick(clock, "departure_rejected", status=status, code=_error_code(payload))
        return summarize_tick(clock, "departure", status=status)

    available = [
        spot["code"]
        for spot in occupancy.get("spots", [])
        if spot.get("status") == "available"
    ]
    protected = plates_inside_reservation(reservation_items, moment)
    owned = [
        item["plate_number"]
        for item in _own_sessions(session_items)
        if item["plate_number"] not in protected
    ]
    action = choose_gate_action(available, owned, rng)
    if action is None:
        return summarize_tick(clock, "idle")

    kind, target = action
    if kind == "entry":
        plates = {item.get("plate_number") for item in session_items}
        plate = generate_plate(rng)
        while plate in plates:
            plate = generate_plate(rng)
        status, payload = client.request(
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

    status, payload = client.request("POST", "/exits", {"plate_number": target})
    if status != 200:
        return summarize_tick(clock, "exit_rejected", status=status, code=_error_code(payload))
    return summarize_tick(clock, "exit", status=status)


def main() -> None:
    dotenv_values(ROOT / ".env")
    setup_logging(get_settings())
    email, password = simulator_credentials()
    database_url = isolated_database_url()
    engine = create_engine(normalize_database_url(database_url))
    client = SimulatorClient(email, password)
    if not client.login():
        raise SystemExit("Simulator sign-in failed.")
    request_every = request_every_ticks()
    rng = random.Random()
    logger.info(
        "simulator started facility=%s interval_seconds=%s clock_step_minutes=%s request_every_ticks=%s",
        FACILITY_ID,
        EVENT_INTERVAL_SECONDS,
        int(CLOCK_STEP.total_seconds() // 60),
        request_every,
    )
    tick = 0
    try:
        while True:
            try:
                logger.info(run_once(rng, engine, client, tick=tick, request_every=request_every))
            except Exception as exc:
                logger.error("simulator tick failed error=%s", type(exc).__name__)
            tick += 1
            time.sleep(EVENT_INTERVAL_SECONDS)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
