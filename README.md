# Parkify

Parkify is a real-time smart parking platform for garage occupancy, sessions, and reservations.

## Features

- 3D parking map, active sessions, reservations, analytics, and facility settings.
- Flask API for spots, sessions, reservations, pricing, gate activity, dashboard, analytics, and settings.
- Neon PostgreSQL. Occupancy comes from sessions, reservations, and maintenance.
- Docker Compose for the React frontend and the Flask API.

## Architecture

Controller → Service → Repository → Database.

## Quickstart

Copy `.env.example` to `.env` and set the Neon URLs. Do not commit `.env`.

- `DATABASE_URL` — pooled URL for the API
- `MIGRATION_DATABASE_URL` — direct URL for Alembic
- `TEST_DATABASE_URL` — a separate Neon branch for tests

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

## API Examples

```bash
curl -s http://127.0.0.1:5001/api/health
curl -s "http://127.0.0.1:5001/api/facilities/facility-skyline/spots?status=available"
curl -s http://127.0.0.1:5001/api/facilities/facility-skyline/dashboard
curl -s http://127.0.0.1:5001/api/facilities/facility-skyline/settings
```

## Testing

```bash
pytest -v
docker compose --profile test run --rm --no-deps -T --build backend-test
```

Database tests use `TEST_DATABASE_URL` and roll back. They skip when that URL is missing or points at the primary database.

## Future Improvements

- Redis cache (planned). Cache-Aside in the service layer for dashboard, analytics, and settings, with TTL, invalidation, database fallback, Docker Compose, tests, and benchmarks. Postponed because PostgreSQL meets current performance needs.
- Authentication.
- Connect the React app to this API. The UI still uses local mock data.
