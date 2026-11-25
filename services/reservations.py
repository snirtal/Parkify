"""Reservation lifecycle.

Overlap is rejected before the database exclusion constraint is reached.
The constraint remains the backstop for two transactions that pass the
check at the same time. Cancelled rows do not occupy a spot.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from models.orm import Reservation

from services.exceptions import ConflictError, NotFoundError, ValidationError
from services.results import ReservationView, reservation_view
from services.rules import (
    apply_reservation_lifecycle,
    effective_reservation_status,
    initial_reservation_status,
    session_blocks_reservation,
)
from services.support import (
    Clock,
    IdFactory,
    clean_plate,
    facility_moment,
    lock_vehicle,
    require_facility,
    run_in_transaction,
)

logger = logging.getLogger("parkify.service.reservations")
OPEN_STATUSES = frozenset({"Active", "Scheduled"})


class ReservationService:
    """Create, update, cancel, and read reservations for one facility."""

    def __init__(self, uow_factory: Callable, clock: Clock, ids: IdFactory) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids

    def create_reservation(
        self,
        facility_id: str,
        plate_number: str,
        spot_code: str,
        starts_at: datetime,
        ends_at: datetime,
        *,
        driver_name: str | None = None,
    ) -> ReservationView:
        return run_in_transaction(
            self._uow_factory,
            lambda uow: self._create(
                uow, facility_id, plate_number, spot_code, starts_at, ends_at, driver_name
            ),
        )

    def get_reservation(self, facility_id: str, reservation_id: str) -> ReservationView:
        def work(uow) -> ReservationView:
            facility = require_facility(uow.repositories, facility_id)
            moment = facility_moment(self._clock, facility, None)
            reservation = self._reservation_in_facility(uow.repositories, facility_id, reservation_id)
            return _view(reservation, moment)

        return run_in_transaction(self._uow_factory, work)

    def list_reservations(
        self,
        facility_id: str,
        *,
        status: str | None = None,
        spot_code: str | None = None,
        plate_number: str | None = None,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
    ) -> list[ReservationView]:
        if status is not None and status not in {"Active", "Scheduled", "Completed", "Cancelled"}:
            raise ValidationError("Reservation status is not recognized.")
        _validate_window(range_start, range_end, allow_empty=True)

        def work(uow) -> list[ReservationView]:
            repos = uow.repositories
            facility = require_facility(repos, facility_id)
            moment = facility_moment(self._clock, facility, None)
            spot_id = None
            if spot_code is not None:
                spot_id = self._spot_in_facility(repos, facility_id, spot_code).id
            vehicle_id = None
            if plate_number is not None:
                plate = clean_plate(plate_number)
                vehicle = repos.vehicles.get_by_plate(plate)
                if vehicle is None:
                    return []
                vehicle_id = vehicle.id
            rows = repos.reservations.list_filtered(
                spot_id=spot_id,
                vehicle_id=vehicle_id,
                range_start=range_start,
                range_end=range_end,
                include_cancelled=True,
            )
            spot_ids = {spot.id for spot in repos.spots.list_for_facility(facility_id)}
            views = []
            for reservation in rows:
                if reservation.spot_id not in spot_ids:
                    continue
                view = _view(reservation, moment)
                if status is not None and view.effective_status != status:
                    continue
                views.append(view)
            return views

        return run_in_transaction(self._uow_factory, work)

    def update_reservation(
        self,
        facility_id: str,
        reservation_id: str,
        *,
        plate_number: str | None = None,
        spot_code: str | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        driver_name: str | None = None,
    ) -> ReservationView:
        if all(
            value is None
            for value in (plate_number, spot_code, starts_at, ends_at, driver_name)
        ):
            raise ValidationError("Provide at least one reservation field to update.")
        return run_in_transaction(
            self._uow_factory,
            lambda uow: self._update(
                uow,
                facility_id,
                reservation_id,
                plate_number=plate_number,
                spot_code=spot_code,
                starts_at=starts_at,
                ends_at=ends_at,
                driver_name=driver_name,
            ),
        )

    def cancel_reservation(self, facility_id: str, reservation_id: str) -> ReservationView:
        return run_in_transaction(
            self._uow_factory,
            lambda uow: self._cancel(uow, facility_id, reservation_id),
        )

    def refresh_lifecycle(self, facility_id: str) -> list[ReservationView]:
        """Persist status changes implied by the facility clock."""
        return run_in_transaction(
            self._uow_factory,
            lambda uow: self._refresh(uow, facility_id),
        )

    def _create(self, uow, facility_id, plate_number, spot_code, starts_at, ends_at, driver_name):
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        moment = facility_moment(self._clock, facility, None)
        starts_at, ends_at = _require_window(starts_at, ends_at)
        plate = clean_plate(plate_number)
        requested_spot = self._spot_in_facility(repos, facility_id, spot_code)
        locked_spots, vehicle = self._lock_spot_and_vehicle(
            uow,
            spots=[requested_spot],
            current_vehicle=repos.vehicles.get_by_plate(plate),
            plate=plate,
            driver_name=driver_name,
        )
        spot = locked_spots[requested_spot.id]
        self._ensure_spot_available(repos, spot, starts_at, ends_at, moment, exclude_id=None)
        self._ensure_vehicle_available(repos, vehicle.id, starts_at, ends_at, exclude_id=None)
        reservation = repos.reservations.add(
            Reservation(
                id=self._ids("res"),
                spot_id=spot.id,
                vehicle_id=vehicle.id,
                status=initial_reservation_status(starts_at, ends_at, moment),
                starts_at=starts_at,
                ends_at=ends_at,
                is_seeded=False,
            )
        )
        reservation.spot = spot
        reservation.vehicle = vehicle
        logger.info("create_reservation reservation=%s spot=%s", reservation.id, spot.code)
        return _view(reservation, moment)

    def _update(self, uow, facility_id, reservation_id, *, plate_number, spot_code, starts_at, ends_at, driver_name):
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        moment = facility_moment(self._clock, facility, None)
        reservation = self._reservation_in_facility(repos, facility_id, reservation_id)
        apply_reservation_lifecycle(reservation, moment)
        if reservation.status not in OPEN_STATUSES:
            raise ConflictError(
                "This reservation can no longer be changed.",
                code="reservation_closed",
            )
        plate = clean_plate(plate_number) if plate_number is not None else reservation.vehicle.plate_number
        target_spot = self._spot_in_facility(
            repos,
            facility_id,
            spot_code if spot_code is not None else reservation.spot.code,
        )
        target_vehicle = repos.vehicles.get_by_plate(plate)
        locked_spots, vehicle = self._lock_spot_and_vehicle(
            uow,
            spots=[reservation.spot, target_spot],
            current_vehicle=reservation.vehicle,
            extra_vehicle=target_vehicle,
            plate=plate,
            driver_name=driver_name,
        )
        spot = locked_spots[target_spot.id]
        new_start = starts_at if starts_at is not None else reservation.starts_at
        new_end = ends_at if ends_at is not None else reservation.ends_at
        new_start, new_end = _require_window(new_start, new_end)
        self._ensure_spot_available(
            repos, spot, new_start, new_end, moment, exclude_id=reservation.id
        )
        self._ensure_vehicle_available(
            repos, vehicle.id, new_start, new_end, exclude_id=reservation.id
        )
        reservation.spot_id = spot.id
        reservation.vehicle_id = vehicle.id
        reservation.starts_at = new_start
        reservation.ends_at = new_end
        reservation.status = initial_reservation_status(new_start, new_end, moment)
        reservation.spot = spot
        reservation.vehicle = vehicle
        logger.info("update_reservation reservation=%s", reservation.id)
        return _view(reservation, moment)

    def _cancel(self, uow, facility_id, reservation_id) -> ReservationView:
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        moment = facility_moment(self._clock, facility, None)
        reservation = self._reservation_in_facility(repos, facility_id, reservation_id)
        apply_reservation_lifecycle(reservation, moment)
        if reservation.status == "Cancelled":
            raise ConflictError("This reservation is already cancelled.", code="reservation_closed")
        if reservation.status == "Completed":
            raise ConflictError(
                "This reservation can no longer be changed.",
                code="reservation_closed",
            )
        reservation.status = "Cancelled"
        logger.info("cancel_reservation reservation=%s", reservation.id)
        return _view(reservation, moment)

    def _refresh(self, uow, facility_id) -> list[ReservationView]:
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        moment = facility_moment(self._clock, facility, None)
        spot_ids = {spot.id for spot in repos.spots.list_for_facility(facility_id)}
        views = []
        for reservation in repos.reservations.list_filtered(include_cancelled=True):
            if reservation.spot_id not in spot_ids:
                continue
            apply_reservation_lifecycle(reservation, moment)
            views.append(_view(reservation, moment))
        logger.info("refresh_lifecycle facility=%s count=%s", facility_id, len(views))
        return views

    def _ensure_spot_available(self, repos, spot, starts_at, ends_at, moment, exclude_id):
        if spot.maintenance_reason:
            raise ConflictError(
                f"Space {spot.code} is offline for maintenance and cannot be reserved.",
                code="spot_unavailable",
            )
        overlaps = [
            item
            for item in repos.reservations.list_overlapping(spot.id, starts_at, ends_at)
            if item.id != exclude_id
        ]
        if overlaps:
            raise ConflictError(
                f"Space {spot.code} already has a reservation in that time range.",
                code="reservation_overlap",
            )
        open_session = repos.sessions.get_active_for_spot(spot.id)
        if open_session is not None and session_blocks_reservation(
            open_session, starts_at, ends_at, moment
        ):
            raise ConflictError(
                f"Space {spot.code} has an active parking session in that time range.",
                code="spot_occupied",
            )

    def _ensure_vehicle_available(self, repos, vehicle_id, starts_at, ends_at, exclude_id):
        overlaps = [
            item
            for item in repos.reservations.list_filtered(
                vehicle_id=vehicle_id,
                range_start=starts_at,
                range_end=ends_at,
                include_cancelled=False,
            )
            if item.id != exclude_id
        ]
        if overlaps:
            raise ConflictError(
                "This vehicle already has a reservation in that time range.",
                code="reservation_overlap",
            )

    def _lock_spot_and_vehicle(
        self,
        uow,
        *,
        spots,
        current_vehicle,
        plate: str,
        driver_name: str | None,
        extra_vehicle=None,
    ):
        """Lock spots by id, then vehicles by id, and return the target pair.

        Spot locks always precede vehicle locks. Several spots or vehicles are
        locked from lowest id to highest so two updates cannot deadlock by
        taking the opposite order. Overlap checks happen after this returns.
        """
        repos = uow.repositories
        locked_spots = _lock_sorted(spots, lambda spot: repos.spots.get_for_update(spot.id))
        if extra_vehicle is None:
            extra_vehicle = repos.vehicles.get_by_plate(plate)
            if extra_vehicle is not None and current_vehicle is not None and extra_vehicle.id == current_vehicle.id:
                extra_vehicle = current_vehicle
        vehicles = [vehicle for vehicle in (current_vehicle, extra_vehicle) if vehicle is not None]
        locked_vehicles = _lock_sorted(vehicles, lambda vehicle: lock_vehicle(repos, vehicle))
        if extra_vehicle is not None:
            target = locked_vehicles[extra_vehicle.id]
        elif current_vehicle is not None and plate == current_vehicle.plate_number:
            target = locked_vehicles[current_vehicle.id]
        else:
            target = None
        if target is None:
            from models.orm import Vehicle

            created = repos.vehicles.add(
                Vehicle(id=self._ids("veh"), plate_number=plate, driver_name=driver_name)
            )
            uow.flush()
            target = lock_vehicle(repos, created)
        elif driver_name and not target.driver_name:
            target.driver_name = driver_name
        return locked_spots, target

    def _spot_in_facility(self, repos, facility_id: str, spot_code: str):
        spot = repos.spots.get_by_code(spot_code.strip().upper())
        if spot is None or spot.floor is None or spot.floor.facility_id != facility_id:
            raise NotFoundError("Parking spot was not found in this facility.")
        return spot

    def _reservation_in_facility(self, repos, facility_id: str, reservation_id: str) -> Reservation:
        reservation = repos.reservations.get(reservation_id)
        if reservation is None or reservation.spot is None or reservation.spot.floor is None:
            raise NotFoundError("Reservation was not found.")
        if reservation.spot.floor.facility_id != facility_id:
            raise NotFoundError("Reservation was not found.")
        if reservation.vehicle is None:
            raise NotFoundError("Reservation was not found.")
        return reservation


def _lock_sorted(items, lock):
    """Lock distinct rows from lowest id to highest and keep that order."""
    locked = {}
    for item in sorted(items, key=lambda row: row.id):
        if item.id in locked:
            continue
        row = lock(item)
        if row is None:
            raise NotFoundError("Parking spot was not found in this facility.")
        locked[row.id] = row
    return locked


def _require_window(starts_at: datetime | None, ends_at: datetime | None) -> tuple[datetime, datetime]:
    if starts_at is None or ends_at is None:
        raise ValidationError("A reservation needs both a start and an end.")
    if starts_at.tzinfo is not None or ends_at.tzinfo is not None:
        raise ValidationError("Timestamps must be facility-local values without a time zone.")
    if ends_at <= starts_at:
        raise ValidationError("End time must be later than start time.")
    return starts_at, ends_at


def _validate_window(starts_at: datetime | None, ends_at: datetime | None, *, allow_empty: bool) -> None:
    if starts_at is None and ends_at is None and allow_empty:
        return
    if starts_at is not None and starts_at.tzinfo is not None:
        raise ValidationError("Timestamps must be facility-local values without a time zone.")
    if ends_at is not None and ends_at.tzinfo is not None:
        raise ValidationError("Timestamps must be facility-local values without a time zone.")
    if starts_at is not None and ends_at is not None and ends_at <= starts_at:
        raise ValidationError("End time must be later than start time.")


def _view(reservation: Reservation, moment: datetime) -> ReservationView:
    plate = reservation.vehicle.plate_number if reservation.vehicle is not None else ""
    driver = reservation.vehicle.driver_name if reservation.vehicle is not None else None
    code = reservation.spot.code if reservation.spot is not None else ""
    return reservation_view(
        reservation,
        spot_code=code,
        plate_number=plate,
        driver_name=driver,
        effective_status=effective_reservation_status(reservation, moment),
    )
