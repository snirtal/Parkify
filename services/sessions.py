"""Start and complete parking sessions.

A start writes the session and its entry gate event in one transaction.
A completion writes the session end, the charge is calculated but not
stored, and the exit gate event is written in that same transaction.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from models.orm import GateActivity, ParkingSession, Vehicle

from services.exceptions import ConflictError, NotFoundError, ValidationError
from services.pricing import PricingService
from services.results import GateEventView, SessionChange, SessionView, session_view
from services.rules import (
    apply_reservation_lifecycle,
    default_gate_name,
    derive_status,
    format_duration,
)
from services.support import (
    Clock,
    IdFactory,
    clean_plate,
    facility_moment,
    lock_vehicle,
    require_facility,
    require_settings,
    run_in_transaction,
)

logger = logging.getLogger("parkify.service.sessions")


class ParkingSessionService:
    """Parking visits for vehicles that do and do not have a reservation."""

    def __init__(
        self,
        uow_factory: Callable,
        clock: Clock,
        ids: IdFactory,
        pricing: PricingService,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._pricing = pricing

    def start_session(
        self,
        facility_id: str,
        plate_number: str,
        spot_code: str,
        *,
        gate_name: str | None = None,
        at: datetime | None = None,
        driver_name: str | None = None,
    ) -> SessionChange:
        """Open a session when the spot and vehicle are both free to park."""
        return run_in_transaction(
            self._uow_factory,
            lambda uow: self._start(
                uow,
                facility_id,
                plate_number,
                spot_code,
                gate_name=gate_name,
                at=at,
                driver_name=driver_name,
            ),
        )

    def complete_session(
        self,
        facility_id: str,
        *,
        plate_number: str | None = None,
        session_id: str | None = None,
        gate_name: str | None = None,
        at: datetime | None = None,
    ) -> SessionChange:
        """Close the active session and return the calculated charge."""
        return run_in_transaction(
            self._uow_factory,
            lambda uow: self._complete(
                uow,
                facility_id,
                plate_number=plate_number,
                session_id=session_id,
                gate_name=gate_name,
                at=at,
            ),
        )

    def list_active_sessions(self, facility_id: str) -> list[SessionView]:
        def work(uow) -> list[SessionView]:
            repos = uow.repositories
            require_facility(repos, facility_id)
            spots = {spot.id: spot for spot in repos.spots.list_for_facility(facility_id)}
            views = []
            for session in repos.sessions.list_active():
                spot = spots.get(session.spot_id)
                if spot is None or session.vehicle is None:
                    continue
                views.append(
                    session_view(
                        session,
                        spot_code=spot.code,
                        plate_number=session.vehicle.plate_number,
                    )
                )
            return views

        return run_in_transaction(self._uow_factory, work)

    def _start(self, uow, facility_id, plate_number, spot_code, *, gate_name, at, driver_name):
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        moment = facility_moment(self._clock, facility, at)
        plate = clean_plate(plate_number)
        spot = self._lock_spot(repos, facility_id, spot_code)
        open_session = repos.sessions.get_active_for_spot(spot.id)
        covering = list(repos.reservations.list_covering(moment, spot_id=spot.id))
        reservation = covering[0] if covering else None
        status = derive_status(spot, open_session, reservation)
        if status == "occupied":
            raise ConflictError(f"Space {spot.code} is occupied.", code="spot_occupied")
        if status == "unavailable":
            raise ConflictError(
                f"Space {spot.code} is offline for maintenance and cannot be used.",
                code="spot_unavailable",
            )
        if status == "reserved":
            reserved_plate = reservation.vehicle.plate_number if reservation and reservation.vehicle else None
            if reserved_plate != plate:
                raise ConflictError(
                    f"Space {spot.code} is reserved for another vehicle.",
                    code="spot_reserved",
                )

        vehicle = self._lock_or_create_vehicle(uow, plate, driver_name)
        if any(item.ended_at is None for item in repos.sessions.list_for_vehicle(vehicle.id)):
            raise ConflictError(
                "This vehicle already has an active parking session.",
                code="vehicle_already_parked",
            )
        holds = list(repos.reservations.list_covering(moment, vehicle_id=vehicle.id))
        other_hold = next((item for item in holds if item.spot_id != spot.id), None)
        if other_hold is not None:
            other_code = other_hold.spot.code if other_hold.spot is not None else other_hold.spot_id
            raise ConflictError(
                f"This vehicle already has a reservation on {other_code}.",
                code="reservation_overlap",
            )
        linked = next((item for item in holds if item.spot_id == spot.id), None)

        session = repos.sessions.add(
            ParkingSession(
                id=self._ids("ses"),
                spot_id=spot.id,
                vehicle_id=vehicle.id,
                status="Active",
                started_at=moment,
                ended_at=None,
                paid_until=linked.ends_at if linked is not None else None,
                until_caption=linked.ends_at.strftime("%H.%M") if linked is not None else None,
                monitoring_label=None,
                has_alert=False,
            )
        )
        session.spot = spot
        session.vehicle = vehicle
        gate = repos.gate_activities.add(
            GateActivity(
                id=self._ids("gl"),
                spot_id=spot.id,
                vehicle_id=vehicle.id,
                reservation_id=linked.id if linked is not None else None,
                occurred_at=moment,
                direction="entry",
                gate_name=_gate_name(gate_name, spot.code),
                status="Reserved" if linked is not None else "Active",
                duration_label=None,
            )
        )
        gate.spot = spot
        gate.vehicle = vehicle
        logger.info("start_session session=%s spot=%s", session.id, spot.code)
        return SessionChange(
            session=session_view(session, spot_code=spot.code, plate_number=vehicle.plate_number),
            gate_event=_gate_view(gate, spot, vehicle.plate_number),
        )

    def _complete(self, uow, facility_id, *, plate_number, session_id, gate_name, at):
        repos = uow.repositories
        facility = require_facility(repos, facility_id)
        moment = facility_moment(self._clock, facility, at)
        session = self._find_active_session(
            repos,
            facility_id,
            plate_number=plate_number,
            session_id=session_id,
        )
        spot = self._lock_spot(repos, facility_id, session.spot.code if session.spot is not None else "")
        if spot.id != session.spot_id:
            spot = repos.spots.get_for_update(session.spot_id)
        if spot is None:
            raise NotFoundError("Parking spot was not found in this facility.")
        vehicle = lock_vehicle(repos, session.vehicle)
        if moment < session.started_at:
            raise ValidationError("The exit time must not be earlier than the entry time.")

        settings = require_settings(repos, facility_id)
        quote = self._pricing.quote(spot, settings, session.started_at, moment)
        session.status = "Completed"
        session.ended_at = moment
        if (
            settings.reservation_overstay_alert
            and session.paid_until is not None
            and session.paid_until < moment
        ):
            session.has_alert = True
            session.alert_title = session.alert_title or "Reservation overstay"

        for reservation in repos.reservations.list_filtered(
            spot_id=spot.id,
            vehicle_id=vehicle.id,
            include_cancelled=False,
        ):
            apply_reservation_lifecycle(reservation, moment)

        gate = repos.gate_activities.add(
            GateActivity(
                id=self._ids("gl"),
                spot_id=spot.id,
                vehicle_id=vehicle.id,
                reservation_id=None,
                occurred_at=moment,
                direction="exit",
                gate_name=_gate_name(gate_name, spot.code),
                status="Completed",
                duration_label=format_duration(moment - session.started_at),
            )
        )
        gate.spot = spot
        gate.vehicle = vehicle
        logger.info("complete_session session=%s spot=%s", session.id, spot.code)
        return SessionChange(
            session=session_view(session, spot_code=spot.code, plate_number=vehicle.plate_number),
            gate_event=_gate_view(gate, spot, vehicle.plate_number),
            quote=quote,
        )

    def _find_active_session(self, repos, facility_id, *, plate_number, session_id):
        if session_id is None and plate_number is None:
            raise ValidationError("A license plate or session id is required.")
        if session_id is not None:
            session = repos.sessions.get(session_id)
        else:
            plate = clean_plate(plate_number or "")
            vehicle = repos.vehicles.get_by_plate(plate)
            if vehicle is None:
                raise NotFoundError("No active parking session was found for this vehicle.")
            session = next(
                (item for item in repos.sessions.list_for_vehicle(vehicle.id) if item.ended_at is None),
                None,
            )
        if session is None or session.ended_at is not None or session.status != "Active":
            raise ConflictError(
                "No active parking session was found.",
                code="session_not_active",
            )
        spot = session.spot or repos.spots.get(session.spot_id)
        if spot is None or spot.floor is None or spot.floor.facility_id != facility_id:
            raise NotFoundError("No active parking session was found.")
        if session.vehicle is None:
            raise NotFoundError("No active parking session was found.")
        return session

    def _lock_spot(self, repos, facility_id: str, spot_code: str):
        code = spot_code.strip().upper()
        spot = repos.spots.get_by_code(code) if code else None
        if spot is None or spot.floor is None or spot.floor.facility_id != facility_id:
            raise NotFoundError("Parking spot was not found in this facility.")
        locked = repos.spots.get_for_update(spot.id)
        if locked is None or locked.floor is None or locked.floor.facility_id != facility_id:
            raise NotFoundError("Parking spot was not found in this facility.")
        return locked

    def _lock_or_create_vehicle(self, uow, plate: str, driver_name: str | None) -> Vehicle:
        repos = uow.repositories
        vehicle = repos.vehicles.get_by_plate(plate)
        if vehicle is None:
            vehicle = repos.vehicles.add(
                Vehicle(
                    id=self._ids("veh"),
                    plate_number=plate,
                    driver_name=driver_name,
                )
            )
            uow.flush()
        locked = lock_vehicle(repos, vehicle)
        if driver_name and not locked.driver_name:
            locked.driver_name = driver_name
        return locked


def _gate_name(requested: str | None, spot_code: str) -> str:
    if requested is None or not requested.strip():
        return default_gate_name(spot_code)
    name = requested.strip()
    if len(name) > 80:
        raise ValidationError("Gate name must be 80 characters or fewer.")
    return name


def _gate_view(activity: GateActivity, spot, plate_number: str) -> GateEventView:
    zone_code = spot.zone.code if spot.zone is not None else ""
    return GateEventView(
        id=activity.id,
        occurred_at=activity.occurred_at,
        plate_number=plate_number,
        direction=activity.direction,
        gate_name=activity.gate_name,
        spot_code=spot.code,
        zone_code=zone_code,
        status=activity.status,
        duration_label=activity.duration_label,
        reservation_id=activity.reservation_id,
    )
