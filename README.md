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
- Flask backend foundation with application factory, YAML and environment-based configuration, centralized logging, JSON error handling, CORS for local frontend development, and a health-check API.

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

Optional: copy the environment template and adjust values:

```bash
cp .env.example .env
```

Start the Flask API (defaults to `http://127.0.0.1:5001`):

```bash
python app.py
```

Run backend tests:

```bash
pytest
```

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
