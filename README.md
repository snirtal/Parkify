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
pip install -r requirements.txt
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

## Future containers

Docker remains part of the architecture, but Phase 2 does not run containers. Later phases can use Docker Compose for the Flask API, the React frontend, Redis, and Kafka if it is required. Neon PostgreSQL stays outside Docker.

## API Examples

Health check:

```bash
curl -s http://127.0.0.1:5001/api/health
```

Example response:

```json
{
  "status": "ok",
  "service": "Parkify",
  "environment": "development",
  "version": "0.1.0"
}
```
