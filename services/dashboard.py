"""Dashboard figures calculated from stored rows, not from the frontend mock."""

from __future__ import annotations

import logging
from collections.abc import Callable

from services.exceptions import ValidationError
from services.parking import load_occupancy
from services.pricing import PricingService
from services.results import DashboardSnapshot, gate_event_view
from services.rules import HIGH_OCCUPANCY_THRESHOLD
from services.support import Clock, run_in_transaction

logger = logging.getLogger("parkify.service.dashboard")


class DashboardService:
    """Facility summary used by the dashboard and analytics header."""

    def __init__(self, uow_factory: Callable, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._pricing = PricingService()

    def snapshot(self, facility_id: str, *, recent_limit: int = 6) -> DashboardSnapshot:
        if recent_limit < 1 or recent_limit > 100:
            raise ValidationError("Recent activity size must be between 1 and 100.")

        def work(uow) -> DashboardSnapshot:
            repos = uow.repositories
            facility, settings, moment, occupancy = load_occupancy(
                repos, self._clock, facility_id, None, self._pricing
            )
            spot_ids = {spot.spot_id for spot in occupancy.spots}
            active = [
                session
                for session in repos.sessions.list_active()
                if session.spot_id in spot_ids
            ]
            overstay = sum(
                1
                for session in active
                if session.paid_until is not None and session.paid_until < moment
            )
            page = repos.gate_activities.list_page(limit=recent_limit)
            recent = tuple(
                gate_event_view(activity)
                for activity in page.items
                if activity.spot is not None
                and activity.spot.floor is not None
                and activity.spot.floor.facility_id == facility_id
            )
            percentage = occupancy.counts.occupancy_percentage
            logger.debug("snapshot facility=%s occupied=%s", facility_id, occupancy.counts.occupied)
            return DashboardSnapshot(
                facility_id=facility.id,
                facility_name=facility.name,
                snapshot_time=moment,
                counts=occupancy.counts,
                rate_trend=f"{occupancy.counts.occupied}/{occupancy.counts.total} occupied",
                active_sessions=len(active),
                overstay_sessions=overstay,
                high_occupancy_alert_armed=bool(settings.high_occupancy_alert),
                high_occupancy_threshold_percent=HIGH_OCCUPANCY_THRESHOLD,
                above_high_occupancy_threshold=percentage >= HIGH_OCCUPANCY_THRESHOLD,
                reservation_overstay_alert_armed=bool(settings.reservation_overstay_alert),
                space_fault_alert_armed=bool(settings.space_fault_alert),
                floors=occupancy.floors,
                zones=occupancy.zones,
                recent_gate_activity=recent,
            )

        return run_in_transaction(self._uow_factory, work)
