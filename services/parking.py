"""Spot availability. Status is derived for the caller and is not stored."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from models.orm import FacilitySettings, ParkingSession, Reservation

from services.exceptions import NotFoundError
from services.pricing import PricingService
from services.results import (
    FacilityOccupancy,
    FloorOccupancy,
    OccupancyCounts,
    ParkingQuote,
    SpotAvailability,
    ZoneOccupancy,
)
from services.rules import (
    BAY_CLASSES,
    SPOT_STATUSES,
    derive_status,
    matches_code_or_plate,
    occupancy_percentage,
)
from services.support import Clock, facility_moment, require_facility, require_settings, run_in_transaction

logger = logging.getLogger("parkify.service.parking")


class ParkingService:
    """Search spots and summarize availability for a facility, floor, or zone."""

    def __init__(self, uow_factory: Callable, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._pricing = PricingService()

    def summarize(self, facility_id: str, *, at: datetime | None = None) -> FacilityOccupancy:
        """Return derived counts for the whole facility at the facility clock."""
        return run_in_transaction(
            self._uow_factory,
            lambda uow: load_occupancy(uow.repositories, self._clock, facility_id, at, self._pricing)[3],
        )

    def search_spots(
        self,
        facility_id: str,
        *,
        floor_id: str | None = None,
        floor_code: str | None = None,
        zone_id: str | None = None,
        zone_code: str | None = None,
        status: str | None = None,
        bay_class: str | None = None,
        query: str | None = None,
        at: datetime | None = None,
    ) -> list[SpotAvailability]:
        """Filter spots by location, derived status, stall class, or code/plate text."""
        from services.exceptions import ValidationError

        if status is not None and status not in SPOT_STATUSES:
            raise ValidationError("Status must be available, occupied, reserved, or unavailable.")
        if bay_class is not None and bay_class not in BAY_CLASSES:
            raise ValidationError("Bay class is not one of the facility stall classes.")

        def work(uow) -> list[SpotAvailability]:
            occupancy = load_occupancy(
                uow.repositories, self._clock, facility_id, at, self._pricing
            )[3]
            return [
                spot
                for spot in occupancy.spots
                if _matches(
                    spot,
                    floor_id=floor_id,
                    floor_code=floor_code,
                    zone_id=zone_id,
                    zone_code=zone_code,
                    status=status,
                    bay_class=bay_class,
                    query=query,
                )
            ]

        found = run_in_transaction(self._uow_factory, work)
        logger.debug("search_spots facility=%s count=%s", facility_id, len(found))
        return found

    def quote_stay(
        self,
        facility_id: str,
        spot_code: str,
        started_at: datetime,
        ended_at: datetime,
    ) -> ParkingQuote:
        """Price a stay with the existing rules. The amount is not stored."""

        def work(uow) -> ParkingQuote:
            repos = uow.repositories
            require_facility(repos, facility_id)
            settings = require_settings(repos, facility_id)
            spot = repos.spots.get_by_code(spot_code.strip().upper())
            if spot is None or spot.floor is None or spot.floor.facility_id != facility_id:
                raise NotFoundError("Parking spot was not found in this facility.")
            return self._pricing.quote(spot, settings, started_at, ended_at)

        quote = run_in_transaction(self._uow_factory, work)
        logger.debug("quote_stay facility=%s spot=%s", facility_id, spot_code.strip().upper())
        return quote


def load_occupancy(repos, clock: Clock, facility_id: str, at: datetime | None, pricing: PricingService):
    """Load derived occupancy inside the caller's transaction."""
    facility = require_facility(repos, facility_id)
    settings = require_settings(repos, facility_id)
    moment = facility_moment(clock, facility, at)
    spots = list(repos.spots.list_for_facility(facility_id))
    open_by_spot: dict[str, ParkingSession] = {}
    for session in repos.sessions.list_active():
        open_by_spot.setdefault(session.spot_id, session)
    cover_by_spot: dict[str, Reservation] = {}
    for reservation in repos.reservations.list_covering(moment):
        cover_by_spot.setdefault(reservation.spot_id, reservation)

    availability: list[SpotAvailability] = []
    floor_totals: dict[str, dict] = {}
    zone_totals: dict[str, dict] = {}
    counts = {name: 0 for name in SPOT_STATUSES}
    for spot in spots:
        decision = derive_status(
            spot,
            open_by_spot.get(spot.id),
            cover_by_spot.get(spot.id),
        )
        counts[decision] += 1
        view = _spot_view(
            spot,
            decision,
            open_by_spot.get(spot.id),
            cover_by_spot.get(spot.id),
            settings,
            pricing,
        )
        availability.append(view)
        _accumulate(floor_totals, spot.floor_id, _floor_seed(spot), decision)
        _accumulate(zone_totals, spot.zone_id, _zone_seed(spot), decision)

    total = len(spots)
    occupancy = FacilityOccupancy(
        counts=OccupancyCounts(
            total=total,
            available=counts["available"],
            occupied=counts["occupied"],
            reserved=counts["reserved"],
            unavailable=counts["unavailable"],
            occupancy_percentage=occupancy_percentage(counts["occupied"], total),
        ),
        floors=tuple(_floor_view(item) for item in floor_totals.values()),
        zones=tuple(_zone_view(item) for item in zone_totals.values()),
        spots=tuple(availability),
    )
    return facility, settings, moment, occupancy


def _spot_view(spot, status, session, reservation, settings: FacilitySettings, pricing: PricingService):
    plate = None
    session_id = None
    reservation_id = None
    reserved_until = None
    if status == "occupied" and session is not None and session.vehicle is not None:
        plate = session.vehicle.plate_number
        session_id = session.id
    elif status == "reserved" and reservation is not None:
        if reservation.vehicle is not None:
            plate = reservation.vehicle.plate_number
        reservation_id = reservation.id
        reserved_until = reservation.ends_at
    return SpotAvailability(
        spot_id=spot.id,
        code=spot.code,
        floor_id=spot.floor_id,
        floor_code=spot.floor.code,
        zone_id=spot.zone_id,
        zone_code=spot.zone.code,
        zone_name=spot.zone.name,
        bay_class=spot.bay_class,
        status=status,
        hourly_rate=pricing.displayed_hourly_rate(spot, settings),
        maintenance_reason=spot.maintenance_reason,
        plate_number=plate,
        session_id=session_id,
        reservation_id=reservation_id,
        reserved_until=reserved_until,
    )


def _floor_seed(spot) -> dict:
    return {
        "floor_id": spot.floor_id,
        "code": spot.floor.code,
        "name": spot.floor.name,
        "occupied": 0,
        "reserved": 0,
        "unavailable": 0,
        "available": 0,
        "capacity": 0,
    }


def _zone_seed(spot) -> dict:
    return {
        "zone_id": spot.zone_id,
        "code": spot.zone.code,
        "name": spot.zone.name,
        "category": spot.zone.dashboard_category,
        "floor_id": spot.floor_id,
        "floor_code": spot.floor.code,
        "occupied": 0,
        "reserved": 0,
        "unavailable": 0,
        "available": 0,
        "capacity": 0,
    }


def _accumulate(buckets: dict, key: str, seed: dict, status: str) -> None:
    bucket = buckets.setdefault(key, seed)
    bucket[status] += 1
    bucket["capacity"] += 1


def _floor_view(bucket: dict) -> FloorOccupancy:
    return FloorOccupancy(**bucket)


def _zone_view(bucket: dict) -> ZoneOccupancy:
    return ZoneOccupancy(**bucket)


def _matches(spot: SpotAvailability, **filters) -> bool:
    if filters["floor_id"] is not None and spot.floor_id != filters["floor_id"]:
        return False
    if filters["floor_code"] is not None and spot.floor_code != filters["floor_code"]:
        return False
    if filters["zone_id"] is not None and spot.zone_id != filters["zone_id"]:
        return False
    if filters["zone_code"] is not None and spot.zone_code != filters["zone_code"]:
        return False
    if filters["status"] is not None and spot.status != filters["status"]:
        return False
    if filters["bay_class"] is not None and spot.bay_class != filters["bay_class"]:
        return False
    return matches_code_or_plate(spot.code, spot.plate_number, filters["query"])
