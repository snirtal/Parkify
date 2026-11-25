"""Historical occupancy calculated only from stored parking sessions.

The frontend hourly curve is a fixed illustration. This service does not
return those points. When no stored session covers the requested range,
the result has no points.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from services.exceptions import ValidationError
from services.parking import load_occupancy
from services.pricing import PricingService
from services.results import FloorOccupancy, OccupancyPoint, OccupancySeries, ZoneOccupancy
from services.rules import occupancy_percentage, session_covers_instant
from services.support import Clock, facility_moment, require_facility, run_in_transaction

logger = logging.getLogger("parkify.service.analytics")

OCCUPANCY_SERIES_DEFINITION = (
    "Each point is the number of distinct parking spots with a stored session "
    "covering the start of that bucket. A completed session covers its "
    "half-open facility-local interval. An open session covers instants from "
    "its start through the facility clock and is not extended into the future. "
    "The percentage divides that count by every spot in the facility, including "
    "reserved and unavailable spots. A requested range whose buckets are all "
    "unoccupied returns no points instead of a fabricated curve."
)
MAX_BUCKETS = 1500


class AnalyticsService:
    """Occupancy over time and the current floor and zone breakdown."""

    def __init__(self, uow_factory: Callable, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._pricing = PricingService()

    def occupancy_over_time(
        self,
        facility_id: str,
        start: datetime,
        end: datetime,
        *,
        bucket_minutes: int = 60,
    ) -> OccupancySeries:
        self._validate_range(start, end, bucket_minutes)

        def work(uow) -> OccupancySeries:
            repos = uow.repositories
            facility = require_facility(repos, facility_id)
            clock = facility_moment(self._clock, facility, None)
            spots = list(repos.spots.list_for_facility(facility_id))
            capacity = len(spots)
            spot_ids = {spot.id for spot in spots}
            sessions = [
                session
                for session in repos.sessions.list_overlapping_interval(start, end)
                if session.spot_id in spot_ids
            ]
            step = timedelta(minutes=bucket_minutes)
            points: list[OccupancyPoint] = []
            cursor = start
            while cursor < end:
                bucket_end = min(end, cursor + step)
                occupied = len(
                    {
                        session.spot_id
                        for session in sessions
                        if session_covers_instant(session, cursor, clock=clock)
                    }
                )
                points.append(
                    OccupancyPoint(
                        start=cursor,
                        end=bucket_end,
                        label=cursor.strftime("%Y-%m-%d %H:%M"),
                        occupied=occupied,
                        capacity=capacity,
                        occupancy_percentage=occupancy_percentage(occupied, capacity),
                    )
                )
                cursor = bucket_end
            if not points or all(point.occupied == 0 for point in points):
                logger.info("occupancy_over_time facility=%s history=false", facility_id)
                return OccupancySeries(
                    definition=OCCUPANCY_SERIES_DEFINITION,
                    has_history=False,
                    points=(),
                )
            logger.info("occupancy_over_time facility=%s points=%s", facility_id, len(points))
            return OccupancySeries(
                definition=OCCUPANCY_SERIES_DEFINITION,
                has_history=True,
                points=tuple(points),
            )

        return run_in_transaction(self._uow_factory, work)

    def occupancy_by_zone(self, facility_id: str) -> tuple[ZoneOccupancy, ...]:
        def work(uow) -> tuple[ZoneOccupancy, ...]:
            return load_occupancy(
                uow.repositories, self._clock, facility_id, None, self._pricing
            )[3].zones

        return run_in_transaction(self._uow_factory, work)

    def occupancy_by_floor(self, facility_id: str) -> tuple[FloorOccupancy, ...]:
        def work(uow) -> tuple[FloorOccupancy, ...]:
            return load_occupancy(
                uow.repositories, self._clock, facility_id, None, self._pricing
            )[3].floors

        return run_in_transaction(self._uow_factory, work)

    def _validate_range(self, start: datetime, end: datetime, bucket_minutes: int) -> None:
        if start.tzinfo is not None or end.tzinfo is not None:
            raise ValidationError(
                "Timestamps must be facility-local values without a time zone."
            )
        if end <= start:
            raise ValidationError("The analytics range end must be later than the start.")
        if not isinstance(bucket_minutes, int) or isinstance(bucket_minutes, bool):
            raise ValidationError("Bucket size must be a whole number of minutes.")
        if bucket_minutes < 15 or bucket_minutes > 24 * 60:
            raise ValidationError("Bucket size must be between 15 minutes and 24 hours.")
        buckets = (end - start) / timedelta(minutes=bucket_minutes)
        if buckets > MAX_BUCKETS:
            raise ValidationError("The analytics range produces too many buckets.")
