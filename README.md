# Parkify

Parkify is a real-time smart parking management platform for monitoring 3D garage occupancy, vehicle telemetry, parking sessions, and reservations.

## Features

- React, TypeScript, Vite, and Three.js (`@react-three/fiber` / `@react-three/drei`) frontend workspace (`frontend/`).
- Futuristic dark-violet glassmorphic interface with segmented top navigation, responsive mobile drawer, and facility alert popover.
- Interactive isometric 3D parking garage digital twin with sculpted clearcoat 3D vehicles, surface-painted bay numbers, studio lighting, orbit/zoom camera controls, and deck/status filtering across available, occupied, reserved, and unavailable spaces.
- Dedicated Parking Map view with real-time search by parking space number or vehicle license plate, cross-deck focus, status filters, and camera controls.
- Active Sessions view with license plate and parking space search, direction and session status filters, and direct navigation from assigned space numbers to the Parking Map.
- Reservations management view with search, status filtering, booking creation, editing, cancellation, overlap validation, and synchronized frontend state across Dashboard and Parking Map.
- Analytics view with daily occupancy curve, KPI summary, and per-zone capacity breakdowns distinguishing available, occupied, reserved, and unavailable spaces.
- Facility Settings view for configuring facility profile, pricing tiers, and notification preferences with validation, header synchronization, and `localStorage` persistence.
- Contextual side inspector panel featuring a rotatable 3D vehicle turntable preview for occupied bays, interactive occupancy charts, zone capacity breakdowns, and gate logs derived from a unified simulated dataset.
- Client-side routing via React Router for Dashboard, Parking Map, Active Sessions, Reservations, Analytics, and Settings views.
- Flask backend with an application factory, YAML and environment configuration, logging, JSON errors, and CORS for local frontend development.
- Neon PostgreSQL schema for the facility, floors, zones, spots, vehicles, sessions, reservations, gate activity, settings, and pricing. SQLAlchemy and Alembic manage the connection and migrations. Occupancy is derived from sessions, reservations, and maintenance reasons.

## Quickstart

### Frontend

Install frontend dependencies and start the development server:

```bash
cd frontend
npm install
npm run dev
```

Run lint and production build checks:

```bash
cd frontend
npm run lint
npm run build
```

### Backend

Create and activate a virtual environment, then install Python dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Copy the environment template and replace the placeholders with Neon connection strings. Do not commit `.env`.

```bash
cp .env.example .env
```

Start the Flask API (defaults to `http://127.0.0.1:5001`). Startup does not connect to the database and does not create tables.

```bash
python app.py
```

Run backend tests. Database integration tests are skipped until `TEST_DATABASE_URL` is set, and the summary lists passed, failed, and skipped tests separately.

```bash
pytest -v
```

## Database

Parkify uses Neon PostgreSQL. The database stays outside the application process. Connection strings are read from the environment and are never hard-coded.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Pooled Neon URL used by the Flask app |
| `MIGRATION_DATABASE_URL` | Direct Neon URL used by Alembic. Falls back to `DATABASE_URL` |
| `TEST_DATABASE_URL` | Isolated Neon branch or database used only by pytest |

URLs may use the `postgresql://` form from the Neon dashboard. The app rewrites them to the `psycopg` driver and adds `sslmode=require` when SSL is not already specified.

### Neon setup

1. Create a Neon project and a database for Parkify, for example `parkify`.
2. In the Neon dashboard, copy the **pooled** connection string and set it as `DATABASE_URL` in `.env`. Keep `sslmode=require`.
3. Copy the **direct** connection string (hostname without `-pooler`) and set it as `MIGRATION_DATABASE_URL`. Alembic loads `.env` from the repository root and uses this value for DDL.
4. Create a separate Neon branch, or a second database, for tests. Set its direct connection string as `TEST_DATABASE_URL`. Do not point it at the primary database.
5. Apply the schema and load the facility snapshot:

```bash
source .venv/bin/activate
alembic upgrade head
python -m repositories.seed
pytest -v
```

`alembic upgrade head` reads `.env` itself and creates the tables. `python -m repositories.seed` can be run more than once; it updates the same primary keys instead of inserting duplicates.

### Schema

Occupancy is not a column on `parking_spots`.

- An open `parking_sessions` row (`ended_at` is null) means the spot is occupied. A partial unique index allows only one open session per spot.
- A non-null `maintenance_reason` means the spot is unavailable when it has no open session.
- A non-cancelled `reservations` window that covers the facility clock means the spot is reserved. PostgreSQL rejects overlapping non-cancelled windows on the same spot.
- Otherwise the spot is available.

| Table | Responsibility |
| --- | --- |
| `facilities` | Skyline Autonomous Hub identity and simulated clock |
| `facility_settings` | Hourly rate, daily maximum, grace period, EV surcharge, alert toggles |
| `floors` | Deck P2 (level 2) and Deck P1 (level 1) |
| `parking_zones` | `P2-N`, `P2-S`, `P1-N`, `P1-S` |
| `parking_spots` | 24 stalls (`bay-p201` … `bay-p212`, `bay-p101` … `bay-p112`) and class rates |
| `vehicles` | License plates and the vehicle details known to the frontend |
| `parking_sessions` | Active occupancy and completed visits |
| `reservations` | `res-1` … `res-6` |
| `gate_activities` | `gl-1` … `gl-6`, including the link from `gl-5` to `res-1` |

Relationships: facility to settings and floors; floor to zones and spots; zone to spots; spot to sessions, reservations, and gate activity; vehicle to the same three; reservation to optional gate activity.

Timestamps are stored as facility-local values without a time zone so they match the simulated Chicago clock (`2026-11-25 14:24`). Spots without a gate entry are seeded as starting at 08:00. The two completed visits are reconstructed from their exit time and displayed duration.

The seed snapshot is 1 facility, 2 floors, 4 zones, 24 spots, 22 vehicles, 16 sessions (14 active, 2 completed), 6 reservations, and 6 gate events.

## Repositories

The `repositories/` package is the data-access layer. It is independent of Flask. A caller supplies a SQLAlchemy session, and `build_repositories(session)` returns the PostgreSQL repositories for that session. Repositories stage inserts, updates, and deletes. They do not commit or roll back, so a later service can change several entities in one transaction.

Occupancy is still derived. Spot repositories do not read or write a status column.

```python
from repositories.factory import build_repositories

repos = build_repositories(session)
vehicle = repos.vehicles.get_by_plate("VEL-204X")
active = repos.sessions.list_active()
overlap = repos.reservations.list_overlapping(spot_id, starts_at, ends_at)
page = repos.gate_activities.list_page(direction="entry", limit=20, offset=0)
session.commit()
```

`session.commit()` belongs to the caller. Database errors are logged by exception type and raised as `RepositoryError`, without the connection string.

Run the full test suite from the repository root. Database tests use `TEST_DATABASE_URL` and roll back their transaction. They are skipped when that URL is missing or points at the same Neon endpoint and database as `DATABASE_URL` or `MIGRATION_DATABASE_URL`, including the difference between a pooled host and its direct host.

```bash
source .venv/bin/activate
pytest -v
```

Run the same suite in Docker with the separate test image. `docker compose up` does not start it, and it is not the running backend container. The command builds the `test` target, passes the database URLs from `.env`, and removes the container when pytest exits:

```bash
docker compose --profile test run --rm --no-deps -T --build backend-test
```

Database tests inside that container still use only `TEST_DATABASE_URL`. They skip when it is missing or points at the same Neon endpoint and database as `DATABASE_URL` or `MIGRATION_DATABASE_URL`. The running backend receives `DATABASE_URL` and `SECRET_KEY` only. Its image does not include pytest or the test files.

## Services

The `services/` package is the business layer. It depends on the repository interfaces through `build_services(uow_factory)`. It does not import Flask, does not execute SQL, and does not store derived occupancy. A service opens one unit of work, changes every row that belongs to the operation, then commits. Any failure rolls that unit of work back. Database errors are logged by exception type and raised as `ConflictError` with code `concurrent_update`. Connection strings are not included.

The default clock is the facility's simulated date and time, not the server clock. Timestamps are naive facility-local values. Tests can inject `FixedClock`. Allocation locks every involved spot in identifier order, then every involved vehicle in identifier order, and gives up after 3 seconds if another transaction still holds a lock. A reservation update locks the current vehicle even when the plate does not change, and locks both spots or both vehicles when either one changes. Overlap is checked again after those locks. The partial unique index and the reservation exclusion constraint remain the backstop.

```python
from config.database import create_db_engine
from config.settings import get_settings
from services.factory import build_services
from services.results import FacilitySettingsUpdate
from services.unit_of_work import unit_of_work_factory
from sqlalchemy.orm import sessionmaker

engine = create_db_engine(get_settings().database_url)
services = build_services(unit_of_work_factory(sessionmaker(bind=engine, expire_on_commit=False)))

spots = services.parking.search_spots("facility-skyline", status="available", query="P-210")
started = services.gate.record_entry("facility-skyline", "SVC-100A", "P-210")
finished = services.sessions.complete_session("facility-skyline", plate_number="SVC-100A")
quote = finished.quote
services.settings.update_settings(
    "facility-skyline",
    FacilitySettingsUpdate(grace_period_minutes=20),
)
```

Those calls commit. The automated tests build the same services around the rolled-back `TEST_DATABASE_URL` transaction instead of the application database.

| Service | Methods |
| --- | --- |
| `parking` | `summarize`, `search_spots`, `quote_stay` |
| `sessions` | `start_session`, `complete_session`, `list_active_sessions` |
| `reservations` | `create_reservation`, `get_reservation`, `list_reservations`, `update_reservation`, `cancel_reservation`, `refresh_lifecycle` |
| `pricing` | `displayed_hourly_rate`, `quote` |
| `gate` | `record_entry`, `record_exit`, `list_activity` |
| `dashboard` | `snapshot` |
| `analytics` | `occupancy_over_time`, `occupancy_by_zone`, `occupancy_by_floor` |
| `settings` | `get_settings`, `update_settings` |

### Business rules

- Spot status is occupied when an open session exists, unavailable when `maintenance_reason` is set and there is no open session, reserved when a non-cancelled reservation window contains the facility clock, and available otherwise. The percentage is occupied spots divided by every spot, rounded to one decimal place.
- A vehicle cannot have two open sessions. A spot cannot have two open sessions. Entry to a spot reserved for another plate is rejected. Entry for the plate that holds the current reservation is allowed and records gate status `Reserved`.
- A reservation window must end after it starts. Cancelled rows do not count as overlap. The same spot or the same vehicle cannot have two overlapping non-cancelled windows. A window that contains the facility clock cannot be placed on an occupied spot. On the paid-until date, a window that starts before `paid_until` is also rejected. A later day is not treated as a permanent hold.
- Active and Scheduled reservations can be updated or cancelled. A window that has ended becomes Completed and can no longer be changed. `refresh_lifecycle` persists that transition. Reads also return `effective_status` without writing. Leaving before the window ends does not complete the reservation early, so the spot stays reserved until `ends_at`. An expired reservation that was never used and one whose vehicle did enter both become Completed. The status value does not distinguish them. A fulfilled visit has an entry gate event whose `reservation_id` points at the reservation. An expired reservation with no such entry was not fulfilled. The exit event does not store `reservation_id`.
- Completing a session writes the exit gate event in the same transaction and returns the charge. The schema has no charge column, so the amount is not stored. If the overstay alert is enabled and `paid_until` is earlier than the exit, the session records alert title `Reservation overstay`.
- Gate activity can be filtered and paged. Rejected entry and exit attempts are logged and raised. They are not inserted, because `gate_activities.status` only allows `Active`, `Completed`, and `Reserved`.
- The dashboard counts spaces, the four statuses, occupancy percentage, active sessions, sessions whose paid-until time has passed, floor and zone capacity, and the newest gate events. The high-occupancy threshold is 85 percent, matching the settings screen. The alert toggle arms the watch; `above_high_occupancy_threshold` reports whether the current percentage has reached it.
- Analytics counts distinct spots with a stored session covering each bucket start. Completed sessions use a half-open interval. Open sessions stop at the facility clock and are not projected forward. A range whose buckets are all unoccupied returns no points and `has_history=False`. It does not return the frontend's illustrated curve.

### Pricing assumptions

The settings screen shows rates but never calculates a charge. Until a narrower policy is specified, `PricingService.quote` uses these rules:

- Standard stalls use the facility hourly rate. EV Fast 150kW stalls use that rate plus the EV surcharge. VIP Priority and Accessible stalls keep the rate stored on the stall.
- A stay of at most the grace period is free. Grace is not subtracted from a longer stay.
- Longer stays are billed in started hours. Each facility-local calendar day is rounded up on its own, capped by the facility daily maximum, then added.
- `paid_until` is the time shown on an occupied stall. It does not reduce the charge.
- Operating hours remain a display string. The service checks its length and does not open or close the facility from it. The seeded value is 24/7.

Settings validation matches the screen: hourly rate from 0.01 through 500.00, daily maximum from 0.01 through 2000.00 and at least the hourly rate, grace from 0 through 180 minutes, and EV surcharge from 0.00 through 100.00. Amounts are `Decimal` values with two decimal places.

### Errors

Services raise `ValidationError`, `NotFoundError`, or `ConflictError`. Each has a stable `code` such as `spot_occupied`, `spot_unavailable`, `spot_reserved`, `vehicle_already_parked`, `reservation_overlap`, `reservation_closed`, `session_not_active`, or `concurrent_update`. Controllers map those to HTTP 400, 404, and 409. The JSON body is always `{"error": {"code", "message"}}`.

Service tests that do not need PostgreSQL are in `tests/test_services_unit.py`. Integration tests use the same isolated Neon branch and rollback as the repository tests. `tests/test_services_concurrency.py` commits two temporary rows on that branch, checks that only one entry wins, and deletes those rows. It does not touch the seeded facility.

## Docker

Compose runs two containers on the `parkify` bridge network. Neon PostgreSQL stays outside Docker and is reached with the connection strings in `.env`. Those values are passed when a container starts. They are not copied into either image.

| Container | Image | Published address | Inside the network |
| --- | --- | --- | --- |
| `parkify-backend` | `parkify-backend` | `http://127.0.0.1:5001` | `backend:5001` |
| `parkify-frontend` | `parkify-frontend` | `http://127.0.0.1:5173` | `frontend:80` |

The frontend container serves the built React app and forwards `/api/` to the backend. The backend listens on `0.0.0.0:5001`, writes logs to stdout, and returns the existing JSON errors. Both services publish a Docker health check.

Build and start:

```bash
docker compose up --build -d
```

Follow logs:

```bash
docker compose logs -f
```

Stop and remove the containers. This does not change the Neon database.

```bash
docker compose down
```

Read-only check that the backend container can reach Neon. The command runs `SELECT 1` and does not print the connection string:

```bash
docker compose exec backend python -c "import logging; logging.disable(logging.CRITICAL); from config.database import create_db_engine, check_database_connection; from config.settings import get_settings; check_database_connection(create_db_engine(get_settings().database_url)); print('neon-connectivity ok')"
```

### Troubleshooting

- `DATABASE_URL is not set`: create `.env` from `.env.example` and start the stack again. The image does not contain this file.
- Port 5001 or 5173 is already in use: stop the local `python app.py` or `npm run dev` process, then run `docker compose up -d`.
- Backend health check stays unhealthy: `docker compose logs backend`. The HTTP check calls `GET /api/health` inside the container.
- Frontend returns 502 for `/api/health`: the backend container is not healthy yet. Check `docker compose ps` and the backend logs.
- Neon connectivity fails: confirm the pooled `DATABASE_URL` in `.env` uses `sslmode=require`, then start the backend again. Do not print the URL.
- Docker tests must use `docker compose --profile test run --rm --no-deps -T --build backend-test`. Do not bind-mount the repository over `/app` and do not copy tests into `parkify-backend`.

## Controllers and REST API

Controllers live in `controllers/` and are registered with Flask blueprints. A controller validates the HTTP request, calls one service method, and serializes the result. It does not execute SQL and does not decide occupancy, pricing, or reservation overlap. `build_services(unit_of_work_factory(...))` opens one unit of work per operation, so a gate entry still stores the session and the gate event together, or stores neither.

`GET` requests do not write. `POST /entries` and `POST /exits` call the gate service. `POST /quotes` calculates a charge and does not store it. `POST /reservations/<id>/cancellation` keeps the row and sets its status to Cancelled.

There is no authentication or authorization. Any client that can reach the API can read and change facility data. Add an auth layer before exposing this API beyond a trusted network.

Money and occupancy percentages are JSON strings (`"4.20"`, `"58.3"`) so the decimal scale survives. Timestamps are facility-local `YYYY-MM-DDTHH:MM:SS` values with no `Z` and no offset. Omitted update fields keep their stored values. `null` and JSON floats are rejected. Unknown body fields are ignored.

| Method | Path | Success | Notes |
| --- | --- | --- | --- |
| GET | `/api/health` | 200 | Process health. Does not query the database |
| GET | `/api/facilities/<facility_id>/spots` | 200 | `floor_id`, `floor_code`, `zone_id`, `zone_code`, `status`, `bay_class`, `query` |
| GET | `/api/facilities/<facility_id>/spots/<spot_code>` | 200 | One derived spot |
| GET | `/api/facilities/<facility_id>/occupancy` | 200 | Counts, floors, zones, and spots |
| GET | `/api/facilities/<facility_id>/sessions` | 200 | Active sessions |
| POST | `/api/facilities/<facility_id>/entries` | 201 | Gate entry. Body: `plate_number`, `spot_code`, optional `gate_name`, `driver_name`, `at` |
| POST | `/api/facilities/<facility_id>/exits` | 200 | Gate exit. Body: `plate_number` or `session_id` |
| GET | `/api/facilities/<facility_id>/reservations` | 200 | `status`, `spot_code`, `plate_number`, `range_start`, `range_end` |
| POST | `/api/facilities/<facility_id>/reservations` | 201 | Body: `plate_number`, `spot_code`, `starts_at`, `ends_at`, optional `driver_name` |
| GET | `/api/facilities/<facility_id>/reservations/<reservation_id>` | 200 | Includes `effective_status` |
| PATCH | `/api/facilities/<facility_id>/reservations/<reservation_id>` | 200 | At least one of plate, spot, start, end, or driver |
| POST | `/api/facilities/<facility_id>/reservations/<reservation_id>/cancellation` | 200 | Status becomes Cancelled |
| POST | `/api/facilities/<facility_id>/reservations/lifecycle` | 200 | Persists clock-driven status changes |
| POST | `/api/facilities/<facility_id>/quotes` | 200 | Body: `spot_code`, `started_at`, `ended_at`. Charge is not stored |
| GET | `/api/facilities/<facility_id>/gate-activity` | 200 | `direction`, `status`, `spot_code`, `plate_number`, `occurred_from`, `occurred_to`, `limit` (1–100), `offset` |
| GET | `/api/facilities/<facility_id>/dashboard` | 200 | Optional `recent_limit` (1–100, default 6) |
| GET | `/api/facilities/<facility_id>/analytics/occupancy` | 200 | Required `start` and `end`. Optional `bucket_minutes` (15–1440) |
| GET | `/api/facilities/<facility_id>/analytics/floors` | 200 | Current floor counts |
| GET | `/api/facilities/<facility_id>/analytics/zones` | 200 | Current zone counts |
| GET | `/api/facilities/<facility_id>/settings` | 200 | Facility profile, prices, and alert toggles |
| PATCH | `/api/facilities/<facility_id>/settings` | 200 | Partial update. Rates are decimal strings |

Validation failures return 400. Unknown facilities, spots, reservations, and sessions return 404. Conflicts such as `spot_occupied` and `reservation_overlap` return 409. An unsupported method returns 405. An unexpected failure returns 500 with `internal_server_error` and no stack trace or connection string. Each response is logged as method, path, status, and duration. Bodies and query strings are not logged.

```bash
curl -s http://127.0.0.1:5001/api/health
curl -s "http://127.0.0.1:5001/api/facilities/facility-skyline/spots?status=available"
curl -s http://127.0.0.1:5001/api/facilities/facility-skyline/dashboard
curl -s http://127.0.0.1:5001/api/facilities/facility-skyline/settings
```

Quote request:

```bash
curl -s -X POST http://127.0.0.1:5001/api/facilities/facility-skyline/quotes \
  -H 'Content-Type: application/json' \
  -d '{"spot_code":"P-210","started_at":"2026-11-25T14:24:00","ended_at":"2026-11-25T16:24:00"}'
```

```json
{
  "started_at": "2026-11-25T14:24:00",
  "ended_at": "2026-11-25T16:24:00",
  "duration_seconds": 7200,
  "duration_label": "2h 00m",
  "hourly_rate": "3.50",
  "billable_hours": 2,
  "amount": "7.00",
  "grace_applied": false,
  "daily_maximum": "28.00"
}
```

Entry request. This writes a session and a gate event:

```bash
curl -s -X POST http://127.0.0.1:5001/api/facilities/facility-skyline/entries \
  -H 'Content-Type: application/json' \
  -d '{"plate_number":"API-100","spot_code":"P-210"}'
```

Conflict response:

```json
{
  "error": {
    "code": "spot_occupied",
    "message": "Space P-210 is occupied."
  }
}
```

The message above is the service text for an occupied spot. A second entry for a different reason uses that reason's code.

Controller request tests that do not open a database connection are in `tests/test_api_requests.py`. API integration tests in `tests/test_api.py` use the Flask test client and the rolled-back `TEST_DATABASE_URL` transaction. Run both with the rest of the suite:

```bash
pytest -v
docker compose --profile test run --rm --no-deps -T --build backend-test
```

### Known limitations

- The API does not authenticate callers.
- The React app still reads its local simulated dataset. It uses camelCase fields such as `bayCode` and `plateNumber`. These endpoints use snake_case and are not wired to the frontend.
- The frontend treats a later reservation on the simulated date as a hold. The API reserves a spot only while the window contains the facility clock.
- The frontend creates a gate row when a reservation is saved. The API inserts a gate row only on entry or exit.
- Analytics returns stored session history. It does not return the frontend's illustrated occupancy curve.
- Vehicle reservation overlap is enforced by the service lock, not by a database constraint.
- An expired unused reservation and a fulfilled one both become `Completed`. Fulfillment is an entry gate event whose `reservation_id` is set.
- Rejected gate attempts are logged and returned as errors. They are not stored.
- Calculated charges are returned on exit and on `POST /quotes`. They are not stored.
- `POST /reservations/lifecycle` and every other write changes the database. Use the isolated test branch for experiments. Do not point `TEST_DATABASE_URL` at the primary database.
