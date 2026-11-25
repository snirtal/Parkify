# Parkify

Parkify is a real-time smart parking management platform for monitoring 3D garage occupancy, vehicle telemetry, parking sessions, and reservations.

## Features

- React, TypeScript, Vite, and Three.js (`@react-three/fiber` / `@react-three/drei`) frontend workspace (`frontend/`).
- Futuristic dark-violet glassmorphic interface with segmented top navigation, responsive mobile drawer, and facility alert popover.
- Interactive isometric 3D parking garage digital twin with sculpted clearcoat 3D vehicles, surface-painted bay numbers, studio lighting, orbit/zoom camera controls, and deck/status filtering across available, occupied, reserved, and unavailable spaces.
- Dedicated Parking Map view with real-time search by parking space number or vehicle license plate, cross-deck focus, status filters, and camera controls.
- Active Sessions view with license plate and parking space search, direction and session status filters, and direct navigation from assigned space numbers to the Parking Map.
- Reservations management view with search, status filtering, booking creation, editing, cancellation, overlap validation, and synchronized frontend state across Dashboard and Parking Map.
- Contextual side inspector panel featuring a rotatable 3D vehicle turntable preview for occupied bays, interactive occupancy charts, zone capacity breakdowns, and gate logs derived from a unified simulated dataset.
- Client-side routing via React Router for Dashboard, Parking Map, Active Sessions, Reservations, Analytics, and Settings views.

## Quickstart

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

## API Examples

Backend API endpoints are not yet implemented.
