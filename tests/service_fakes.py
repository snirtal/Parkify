"""In-memory repositories for service tests.

They implement the methods the services call and can roll a transaction
back to the state captured when the unit of work opened.
"""

from __future__ import annotations

from datetime import datetime

from repositories.base import Page
from services.exceptions import ConstraintConflict


def _snapshot(entity) -> dict:
    return {
        key: value
        for key, value in entity.__dict__.items()
        if not key.startswith("_sa_")
    }


def _restore(entity, data: dict) -> None:
    for key, value in data.items():
        setattr(entity, key, value)


class _Rows:
    def __init__(self) -> None:
        self.by_id: dict[str, object] = {}

    def add(self, entity):
        self.by_id[entity.id] = entity
        return entity

    def get(self, entity_id: str):
        return self.by_id.get(entity_id)

    def values(self):
        return list(self.by_id.values())


class MemoryRepositories:
    def __init__(self) -> None:
        self.facilities = _Rows()
        self.settings = _Rows()
        self.spots = _Rows()
        self.vehicles = _Rows()
        self.sessions = _Rows()
        self.reservations = _Rows()
        self.gate_activities = _Rows()
        self.locks: list[tuple[str, str]] = []
        self._settings_by_facility: dict[str, object] = {}

    def mark(self) -> dict:
        return {
            "facilities": {key: _snapshot(value) for key, value in self.facilities.by_id.items()},
            "settings": {key: _snapshot(value) for key, value in self.settings.by_id.items()},
            "spots": {key: _snapshot(value) for key, value in self.spots.by_id.items()},
            "vehicles": {key: _snapshot(value) for key, value in self.vehicles.by_id.items()},
            "sessions": {key: _snapshot(value) for key, value in self.sessions.by_id.items()},
            "reservations": {key: _snapshot(value) for key, value in self.reservations.by_id.items()},
            "gate_activities": {
                key: _snapshot(value) for key, value in self.gate_activities.by_id.items()
            },
            "settings_by_facility": dict(self._settings_by_facility),
        }

    def revert(self, mark: dict) -> None:
        mapping = {
            "facilities": self.facilities,
            "settings": self.settings,
            "spots": self.spots,
            "vehicles": self.vehicles,
            "sessions": self.sessions,
            "reservations": self.reservations,
            "gate_activities": self.gate_activities,
        }
        for name, rows in mapping.items():
            snapshot = mark[name]
            for entity_id in list(rows.by_id):
                if entity_id not in snapshot:
                    del rows.by_id[entity_id]
            for entity_id, data in snapshot.items():
                if entity_id in rows.by_id:
                    _restore(rows.by_id[entity_id], data)
        self._settings_by_facility = {
            key: self.settings.by_id[value.id]
            for key, value in mark["settings_by_facility"].items()
            if value.id in self.settings.by_id
        }

    def accept(self) -> None:
        return None


class MemoryUnitOfWork:
    def __init__(self, repositories: MemoryRepositories, *, fail_commit: bool = False) -> None:
        self.repositories = _Facade(repositories)
        self.fail_commit = fail_commit
        self.committed = False
        self.rolled_back = False
        self._mark = None
        self._store = repositories

    def __enter__(self) -> MemoryUnitOfWork:
        self._mark = self._store.mark()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            self.rollback()

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        if self.fail_commit:
            raise ConstraintConflict("The operation conflicts with existing data.")
        self._store.accept()
        self.committed = True

    def rollback(self) -> None:
        if self._mark is not None:
            self._store.revert(self._mark)
        self.rolled_back = True


class _Facade:
    """Match the Repositories object the services expect."""

    def __init__(self, store: MemoryRepositories) -> None:
        self.facilities = _Facilities(store)
        self.settings = _Settings(store)
        self.spots = _Spots(store)
        self.vehicles = _Vehicles(store)
        self.sessions = _Sessions(store)
        self.reservations = _Reservations(store)
        self.gate_activities = _GateActivities(store)


class _Facilities:
    def __init__(self, store: MemoryRepositories) -> None:
        self._store = store

    def get(self, entity_id: str):
        return self._store.facilities.get(entity_id)


class _Settings:
    def __init__(self, store: MemoryRepositories) -> None:
        self._store = store

    def get_for_facility(self, facility_id: str):
        return self._store._settings_by_facility.get(facility_id)

    def apply_changes(self, settings, **changes):
        for name, value in changes.items():
            if value is not None:
                setattr(settings, name, value)
        return settings


class _Spots:
    def __init__(self, store: MemoryRepositories) -> None:
        self._store = store

    def get(self, entity_id: str):
        return self._store.spots.get(entity_id)

    def get_by_code(self, code: str):
        return next((spot for spot in self._store.spots.values() if spot.code == code), None)

    def get_for_update(self, entity_id: str):
        self._store.locks.append(("spot", entity_id))
        return self.get(entity_id)

    def list_for_facility(self, facility_id: str):
        rows = [
            spot
            for spot in self._store.spots.values()
            if spot.floor is not None and spot.floor.facility_id == facility_id
        ]
        return sorted(rows, key=lambda spot: (spot.floor.level_index, spot.row, spot.slot_index, spot.id))


class _Vehicles:
    def __init__(self, store: MemoryRepositories) -> None:
        self._store = store

    def get(self, entity_id: str):
        return self._store.vehicles.get(entity_id)

    def get_by_plate(self, plate_number: str):
        return next(
            (vehicle for vehicle in self._store.vehicles.values() if vehicle.plate_number == plate_number),
            None,
        )

    def get_for_update(self, entity_id: str):
        self._store.locks.append(("vehicle", entity_id))
        return self.get(entity_id)

    def add(self, entity):
        return self._store.vehicles.add(entity)


class _Sessions:
    def __init__(self, store: MemoryRepositories) -> None:
        self._store = store

    def get(self, entity_id: str):
        return self._store.sessions.get(entity_id)

    def add(self, entity):
        return self._store.sessions.add(entity)

    def list_active(self):
        rows = [session for session in self._store.sessions.values() if session.ended_at is None]
        return sorted(rows, key=lambda session: (session.started_at, session.id))

    def get_active_for_spot(self, spot_id: str):
        return next(
            (
                session
                for session in self.list_active()
                if session.spot_id == spot_id
            ),
            None,
        )

    def list_for_vehicle(self, vehicle_id: str):
        rows = [session for session in self._store.sessions.values() if session.vehicle_id == vehicle_id]
        return sorted(rows, key=lambda session: (session.started_at, session.id))

    def list_overlapping_interval(self, start: datetime, end: datetime):
        rows = []
        for session in self._store.sessions.values():
            if session.started_at < end and (session.ended_at is None or session.ended_at > start):
                rows.append(session)
        return sorted(rows, key=lambda session: (session.started_at, session.id))


class _Reservations:
    def __init__(self, store: MemoryRepositories) -> None:
        self._store = store

    def get(self, entity_id: str):
        return self._store.reservations.get(entity_id)

    def add(self, entity):
        return self._store.reservations.add(entity)

    def list_filtered(
        self,
        *,
        status: str | None = None,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
        include_cancelled: bool = True,
    ):
        rows = []
        for reservation in self._store.reservations.values():
            if status is not None and reservation.status != status:
                continue
            if status is None and not include_cancelled and reservation.status == "Cancelled":
                continue
            if spot_id is not None and reservation.spot_id != spot_id:
                continue
            if vehicle_id is not None and reservation.vehicle_id != vehicle_id:
                continue
            if range_start is not None and reservation.ends_at <= range_start:
                continue
            if range_end is not None and reservation.starts_at >= range_end:
                continue
            rows.append(reservation)
        return sorted(rows, key=lambda reservation: (reservation.starts_at, reservation.id))

    def list_overlapping(self, spot_id: str, starts_at: datetime, ends_at: datetime, *, include_cancelled: bool = False):
        return self.list_filtered(
            spot_id=spot_id,
            range_start=starts_at,
            range_end=ends_at,
            include_cancelled=include_cancelled,
        )

    def list_covering(self, moment: datetime, *, spot_id: str | None = None, vehicle_id: str | None = None):
        rows = [
            reservation
            for reservation in self._store.reservations.values()
            if reservation.status != "Cancelled"
            and reservation.starts_at <= moment < reservation.ends_at
            and (spot_id is None or reservation.spot_id == spot_id)
            and (vehicle_id is None or reservation.vehicle_id == vehicle_id)
        ]
        return sorted(rows, key=lambda reservation: (reservation.starts_at, reservation.id))


class _GateActivities:
    def __init__(self, store: MemoryRepositories) -> None:
        self._store = store

    def add(self, entity):
        return self._store.gate_activities.add(entity)

    def list_page(
        self,
        *,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page:
        rows = []
        for activity in self._store.gate_activities.values():
            if spot_id is not None and activity.spot_id != spot_id:
                continue
            if vehicle_id is not None and activity.vehicle_id != vehicle_id:
                continue
            if direction is not None and activity.direction != direction:
                continue
            if status is not None and activity.status != status:
                continue
            if occurred_from is not None and activity.occurred_at < occurred_from:
                continue
            if occurred_to is not None and activity.occurred_at >= occurred_to:
                continue
            rows.append(activity)
        rows.sort(key=lambda activity: (activity.occurred_at, activity.id), reverse=True)
        return Page(items=rows[offset : offset + limit], total=len(rows), limit=limit, offset=offset)


def add_settings(store: MemoryRepositories, settings) -> None:
    store.settings.add(settings)
    store._settings_by_facility[settings.facility_id] = settings
