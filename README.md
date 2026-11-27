# Parkify

Parkify is a real-time smart parking platform for garage occupancy, sessions, and reservations.

## Features

- 3D parking map, active sessions, reservations, analytics, and facility settings.
- Flask API for spots, sessions, reservations, pricing, gate activity, dashboard, analytics, and settings.
- React app reads and updates that API through `/api`. The backend is the source of truth.
- Neon PostgreSQL. Occupancy comes from sessions, reservations, and maintenance.
- Docker Compose for the React frontend and the Flask API.

## Architecture

Controller → Service → Repository → Database.

## Quickstart

Copy `.env.example` to `.env` and set the Neon URLs. Do not commit `.env`.

- `DATABASE_URL` — pooled URL for the API
- `MIGRATION_DATABASE_URL` — direct URL for Alembic
- `TEST_DATABASE_URL` — a separate Neon branch for tests
- `FACILITY_ID` and `VITE_FACILITY_ID` — optional. Both default to `facility-skyline`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m repositories.seed
docker compose up --build -d
```

API: http://127.0.0.1:5001
Frontend: http://127.0.0.1:5173

`npm run dev` in `frontend/` proxies `/api` to the local API. Docker serves the same paths through Nginx. Do not put database credentials in the frontend.

## Live simulation

`make start` runs the isolated API, frontend, and simulator. When the application is already up, it resumes the simulator only. Events arrive every 5 seconds, and the browser reloads every 2 seconds. `make stop` stops new simulated events and leaves the application open. `make shutdown` stops the isolated API, frontend, and simulator.

`make reset` stops the simulator, asks for confirmation, and deletes only that simulator's vehicles, sessions, gate activity, and reservations from the isolated test database. Seed data stays. The application keeps running and refreshes on its own. The simulator stays stopped.

```bash
make start
make stop
make reset
make shutdown
```

Browser: http://127.0.0.1:5174/

The live stack uses the isolated Neon testing branch. Existing rows stay in place. Production on ports 5001 and 5173 is unchanged.

## API Examples

```bash
curl -s http://127.0.0.1:5001/api/health
curl -s "http://127.0.0.1:5001/api/facilities/facility-skyline/spots?status=available"
curl -s http://127.0.0.1:5001/api/facilities/facility-skyline/dashboard
curl -s http://127.0.0.1:5001/api/facilities/facility-skyline/settings
```

## Testing

```bash
cd frontend && npm test && npm run build
pytest -v
docker compose --profile test run --rm --no-deps -T --build backend-test
```

Database tests use `TEST_DATABASE_URL` and roll back. They skip when that URL is missing or points at the primary database.

## Future Improvements

- Redis cache (planned). Cache-Aside in the service layer for dashboard, analytics, and settings, with TTL, invalidation, database fallback, Docker Compose, tests, and benchmarks. Postponed because PostgreSQL meets current performance needs.
- Authentication.
