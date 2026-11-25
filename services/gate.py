"""Gate entry and exit.

Entry and exit delegate to the parking-session service so the session and
the gate event are written together. A rejected attempt is logged and
raised. It is not stored: gate activity status only allows Active,
Completed, and Reserved.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from services.exceptions import ValidationError
from services.results import GateEventView, GatePage, SessionChange, gate_event_view
from services.sessions import ParkingSessionService
from services.support import Clock, facility_moment, require_facility, run_in_transaction

logger = logging.getLogger("parkify.service.gate")

DIRECTIONS = frozenset({"entry", "exit"})
GATE_STATUSES = frozenset({"Active", "Completed", "Reserved"})


class GateService:
    """Record gate events and list them with the existing filters."""

    def __init__(
        self,
        sessions: ParkingSessionService,
        uow_factory: Callable,
        clock: Clock,
    ) -> None:
        self._sessions = sessions
        self._uow_factory = uow_factory
        self._clock = clock

    def record_entry(
        self,
        facility_id: str,
        plate_number: str,
        spot_code: str,
        *,
        gate_name: str | None = None,
        at: datetime | None = None,
        driver_name: str | None = None,
    ) -> SessionChange:
        try:
            return self._sessions.start_session(
                facility_id,
                plate_number,
                spot_code,
                gate_name=gate_name,
                at=at,
                driver_name=driver_name,
            )
        except Exception as exc:
            code = getattr(exc, "code", type(exc).__name__)
            logger.info("gate entry rejected code=%s spot=%s", code, spot_code)
            raise

    def record_exit(
        self,
        facility_id: str,
        *,
        plate_number: str | None = None,
        session_id: str | None = None,
        gate_name: str | None = None,
        at: datetime | None = None,
    ) -> SessionChange:
        try:
            return self._sessions.complete_session(
                facility_id,
                plate_number=plate_number,
                session_id=session_id,
                gate_name=gate_name,
                at=at,
            )
        except Exception as exc:
            code = getattr(exc, "code", type(exc).__name__)
            logger.info("gate exit rejected code=%s", code)
            raise

    def list_activity(
        self,
        facility_id: str,
        *,
        spot_code: str | None = None,
        plate_number: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> GatePage:
        if direction is not None and direction not in DIRECTIONS:
            raise ValidationError("Gate direction must be entry or exit.")
        if status is not None and status not in GATE_STATUSES:
            raise ValidationError("Gate status must be Active, Completed, or Reserved.")
        if limit < 1 or limit > 100:
            raise ValidationError("Page size must be between 1 and 100.")
        if offset < 0:
            raise ValidationError("Page offset must be zero or greater.")
        for moment in (occurred_from, occurred_to):
            if moment is not None and moment.tzinfo is not None:
                raise ValidationError(
                    "Timestamps must be facility-local values without a time zone."
                )

        def work(uow) -> GatePage:
            repos = uow.repositories
            facility = require_facility(repos, facility_id)
            facility_moment(self._clock, facility, None)
            spot_id = None
            if spot_code is not None:
                spot = repos.spots.get_by_code(spot_code.strip().upper())
                if spot is None or spot.floor is None or spot.floor.facility_id != facility_id:
                    raise ValidationError("Parking spot was not found in this facility.")
                spot_id = spot.id
            vehicle_id = None
            if plate_number is not None:
                from services.support import clean_plate

                vehicle = repos.vehicles.get_by_plate(clean_plate(plate_number))
                if vehicle is None:
                    return GatePage(items=(), total=0, limit=limit, offset=offset)
                vehicle_id = vehicle.id
            page = repos.gate_activities.list_page(
                spot_id=spot_id,
                vehicle_id=vehicle_id,
                direction=direction,
                status=status,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                limit=limit,
                offset=offset,
            )
            items: list[GateEventView] = []
            for activity in page.items:
                if activity.spot is None or activity.spot.floor is None:
                    continue
                if activity.spot.floor.facility_id != facility_id:
                    continue
                items.append(gate_event_view(activity))
            return GatePage(items=tuple(items), total=page.total, limit=page.limit, offset=page.offset)

        return run_in_transaction(self._uow_factory, work)
