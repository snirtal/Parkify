"""Customer reservation requests.

A pending request records a plate, parking type, arrival, and duration.
It does not create a reservation or hold a spot. Approval books one available
spot of the requested type in the same transaction. Rejection and expiry
leave the lot unchanged.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from models.orm import ReservationRequest, Vehicle

from services.exceptions import ConflictError, NotFoundError, ValidationError
from services.reservations import ReservationService, _require_window
from services.results import ReservationRequestView
from services.rules import BAY_CLASSES
from services.support import (
    Clock,
    IdFactory,
    clean_plate,
    facility_moment,
    lock_vehicle,
    require_facility,
    run_in_transaction,
)

logger = logging.getLogger("parkify.service.reservation_requests")
MIN_DURATION_MINUTES = 15
MAX_DURATION_MINUTES = 24 * 60


class ReservationRequestService:
    """Create, review, and expire customer reservation requests."""

    def __init__(
        self,
        uow_factory: Callable,
        clock: Clock,
        ids: IdFactory,
        reservations: ReservationService,
        *,
        request_limit: int = 8,
    ) -> None:
        if request_limit < 1:
            raise ValueError("request_limit must be at least 1")
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._reservations = reservations
        self._request_limit = request_limit

    def create_request(
        self,
        facility_id: str,
        plate_number: str,
        bay_class: str,
        starts_at: datetime,
        ends_at: datetime,
    ) -> ReservationRequestView:
        parking_type = _bay_class(bay_class)
        starts_at, ends_at = _require_window(starts_at, ends_at)
        _duration_minutes(starts_at, ends_at)
        self.expire_elapsed(facility_id)
        return run_in_transaction(
            self._uow_factory,
            lambda uow: self._create(
                uow, facility_id, plate_number, parking_type, starts_at, ends_at
            ),
        )

    def list_requests(
        self,
        facility_id: str,
        *,
        status: str | None = None,
    ) -> list[ReservationRequestView]:
        if status is not None and status not in {"Pending", "Approved", "Rejected", "Expired"}:
            raise ValidationError("Reservation request status is not recognized.")
        self.expire_elapsed(facility_id)

        def work(uow) -> list[ReservationRequestView]:
            require_facility(uow.repositories, facility_id)
            rows = uow.repositories.reservation_requests.list_for_facility(facility_id)
            if status is not None:
                rows = [row for row in rows if row.status == status]
            return [_view(row) for row in rows]

        return run_in_transaction(self._uow_factory, work)

    def approve_request(
        self,
        facility_id: str,
        request_id: str,
        *,
        actor_id: str,
    ) -> ReservationRequestView:
        self.expire_elapsed(facility_id)
        result = run_in_transaction(
            self._uow_factory,
            lambda uow: self._decide(uow, facility_id, request_id, actor_id, approved=True),
        )
        if result is None:
            raise ConflictError(
                "This request expired before it was reviewed.",
                code="reservation_request_expired",
            )
        return result

    def reject_request(
        self,
        facility_id: str,
        request_id: str,
        *,
        actor_id: str,
    ) -> ReservationRequestView:
        self.expire_elapsed(facility_id)
        result = run_in_transaction(
            self._uow_factory,
            lambda uow: self._decide(uow, facility_id, request_id, actor_id, approved=False),
        )
        if result is None:
            raise ConflictError(
                "This request expired before it was reviewed.",
                code="reservation_request_expired",
            )
        return result

    def expire_elapsed(self, facility_id: str) -> int:
        """Close pending requests whose window has already ended."""

        def work(uow) -> int:
            repos = uow.repositories
            facility = require_facility(repos, facility_id)
            self._lock_facility(repos, facility_id)
            moment = facility_moment(self._clock, facility, None)
            expired = 0
            for request in repos.reservation_requests.list_for_facility(facility_id):
                if request.status != "Pending" or request.ends_at > moment:
                    continue
                locked = repos.reservation_requests.get_for_update(request.id)
                if locked is None or locked.status != "Pending" or locked.ends_at > moment:
                    continue
                locked.status = "Expired"
                locked.decided_at = moment
                expired += 1
                logger.info("reservation request expired id=%s", locked.id)
            return expired

        return run_in_transaction(self._uow_factory, work)

    def _create(self, uow, facility_id, plate_number, bay_class, starts_at, ends_at):
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        self._lock_facility(repos, facility_id)
        moment = facility_moment(self._clock, facility, None)
        if ends_at <= moment:
            raise ValidationError("The requested time has already passed.")
        plate = clean_plate(plate_number)
        vehicle = self._vehicle(uow, plate)
        if repos.reservation_requests.pending_for_vehicle(facility_id, vehicle.id) is not None:
            raise ConflictError(
                "This vehicle already has a pending request.",
                code="duplicate_request",
            )
        if repos.reservation_requests.count_pending(facility_id) >= self._request_limit:
            raise ConflictError(
                "The facility already has too many pending requests.",
                code="reservation_request_limit",
            )
        overlaps = repos.reservations.list_filtered(
            vehicle_id=vehicle.id,
            range_start=starts_at,
            range_end=ends_at,
            include_cancelled=False,
        )
        if overlaps:
            raise ConflictError(
                "This vehicle already has a reservation in that time range.",
                code="reservation_overlap",
            )
        request = repos.reservation_requests.add(
            ReservationRequest(
                id=self._ids("rreq"),
                facility_id=facility_id,
                vehicle_id=vehicle.id,
                bay_class=bay_class,
                starts_at=starts_at,
                ends_at=ends_at,
                status="Pending",
            )
        )
        request.vehicle = vehicle
        logger.info("reservation request created id=%s bay_class=%s", request.id, bay_class)
        return _view(request)

    def _decide(self, uow, facility_id, request_id, actor_id, *, approved: bool):
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        self._lock_facility(repos, facility_id)
        if repos.users.get(actor_id) is None:
            raise NotFoundError("Operator was not found.")
        moment = facility_moment(self._clock, facility, None)
        request = self._locked_request(repos, facility_id, request_id)
        if request.status == "Expired":
            raise ConflictError(
                "This request expired before it was reviewed.",
                code="reservation_request_expired",
            )
        if request.status != "Pending":
            raise ConflictError(
                "This request has already been reviewed.",
                code="reservation_request_closed",
            )
        if request.ends_at <= moment:
            request.status = "Expired"
            request.decided_at = moment
            logger.info("reservation request expired id=%s", request.id)
            return None
        if approved:
            if request.vehicle is None:
                raise NotFoundError("Reservation request was not found.")
            booked = self._reservations.book_available_bay(
                uow,
                facility_id,
                request.vehicle.plate_number,
                request.bay_class,
                request.starts_at,
                request.ends_at,
            )
            request.status = "Approved"
            request.reservation_id = booked.id
            request.decided_by_user_id = actor_id
            request.decided_at = moment
            logger.info(
                "reservation request approved id=%s reservation=%s actor=%s",
                request.id,
                booked.id,
                actor_id,
            )
            return _view(request, spot_code=booked.spot_code)
        request.status = "Rejected"
        request.decided_by_user_id = actor_id
        request.decided_at = moment
        logger.info("reservation request rejected id=%s actor=%s", request.id, actor_id)
        return _view(request)

    def _vehicle(self, uow, plate: str) -> Vehicle:
        repos = uow.repositories
        existing = repos.vehicles.get_by_plate(plate)
        if existing is None:
            existing = repos.vehicles.add(Vehicle(id=self._ids("veh"), plate_number=plate))
            uow.flush()
        return lock_vehicle(repos, existing)

    def _locked_request(self, repos, facility_id: str, request_id: str) -> ReservationRequest:
        request = repos.reservation_requests.get_for_update(request_id)
        if request is None or request.facility_id != facility_id:
            raise NotFoundError("Reservation request was not found.")
        return request

    def _lock_facility(self, repos, facility_id: str) -> None:
        locked = repos.facilities.get_for_update(facility_id)
        if locked is None:
            raise NotFoundError("Facility was not found.")


def _bay_class(value: object) -> str:
    if not isinstance(value, str) or value not in BAY_CLASSES:
        raise ValidationError("Parking type must be a known bay class.")
    return value


def _duration_minutes(starts_at: datetime, ends_at: datetime) -> int:
    minutes = int((ends_at - starts_at).total_seconds() // 60)
    if minutes < MIN_DURATION_MINUTES or minutes > MAX_DURATION_MINUTES:
        raise ValidationError("Duration must be between 15 minutes and 24 hours.")
    return minutes


def _view(request: ReservationRequest, spot_code: str | None = None) -> ReservationRequestView:
    plate = request.vehicle.plate_number if request.vehicle is not None else ""
    if spot_code is None and request.reservation is not None and request.reservation.spot is not None:
        spot_code = request.reservation.spot.code
    return ReservationRequestView(
        id=request.id,
        plate_number=plate,
        bay_class=request.bay_class,
        starts_at=request.starts_at,
        ends_at=request.ends_at,
        duration_minutes=_duration_minutes(request.starts_at, request.ends_at),
        status=request.status,
        reservation_id=request.reservation_id,
        spot_code=spot_code,
        decided_at=request.decided_at,
    )
