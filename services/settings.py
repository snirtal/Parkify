"""Facility settings.

Operating hours stay a display string. The settings screen stores values
such as "00:00 – 23:59 (24/7)" and does not define a machine-readable
schedule, so this service checks the length only and does not open or
close the facility from that text.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal

from services.exceptions import ValidationError
from services.pricing import quantize_money
from services.results import FacilitySettingsUpdate, FacilitySettingsView
from services.support import require_facility, require_settings, run_in_transaction

logger = logging.getLogger("parkify.service.settings")


class SettingsService:
    """Read and update the facility profile, prices, and alert toggles."""

    def __init__(self, uow_factory: Callable) -> None:
        self._uow_factory = uow_factory

    def get_settings(self, facility_id: str) -> FacilitySettingsView:
        def work(uow) -> FacilitySettingsView:
            facility = require_facility(uow.repositories, facility_id)
            settings = require_settings(uow.repositories, facility_id)
            return _view(facility, settings)

        return run_in_transaction(self._uow_factory, work)

    def update_settings(
        self,
        facility_id: str,
        changes: FacilitySettingsUpdate,
    ) -> FacilitySettingsView:
        def work(uow) -> FacilitySettingsView:
            repos = uow.repositories
            facility = require_facility(repos, facility_id)
            settings = require_settings(repos, facility_id)
            merged = _merge(facility, settings, changes)
            validated = validate_facility_settings(merged)
            facility.name = validated.facility_name
            facility.address = validated.facility_address
            facility.operating_hours = validated.operating_hours
            repos.settings.apply_changes(
                settings,
                hourly_rate=validated.hourly_rate,
                daily_max_rate=validated.daily_max_rate,
                grace_period_minutes=validated.grace_period_minutes,
                ev_surcharge=validated.ev_surcharge,
                high_occupancy_alert=validated.high_occupancy_alert,
                reservation_overstay_alert=validated.reservation_overstay_alert,
                space_fault_alert=validated.space_fault_alert,
            )
            logger.info("update_settings facility=%s", facility_id)
            return validated

        return run_in_transaction(self._uow_factory, work)


def validate_facility_settings(candidate: FacilitySettingsView) -> FacilitySettingsView:
    """Apply the settings-screen bounds. Monetary results are 2 decimal places."""
    name = _text(candidate.facility_name, "Facility name", minimum=2, maximum=120)
    address = _text(candidate.facility_address, "Facility address", minimum=4, maximum=180)
    hours = _text(candidate.operating_hours, "Operating hours", minimum=3, maximum=80)
    hourly = _money(
        candidate.hourly_rate,
        "Hourly parking rate must be greater than 0.00 and at most 500.00.",
        minimum=Decimal("0.01"),
        maximum=Decimal("500.00"),
    )
    daily = _money(
        candidate.daily_max_rate,
        "Daily maximum rate must be greater than 0.00 and at most 2000.00.",
        minimum=Decimal("0.01"),
        maximum=Decimal("2000.00"),
    )
    if daily < hourly:
        raise ValidationError(
            "Daily maximum rate must be greater than or equal to the hourly parking rate."
        )
    grace = candidate.grace_period_minutes
    if isinstance(grace, bool) or not isinstance(grace, int) or not 0 <= grace <= 180:
        raise ValidationError("Free grace period must be a whole number between 0 and 180 minutes.")
    surcharge = _money(
        candidate.ev_surcharge,
        "EV charging surcharge must be between 0.00 and 100.00.",
        minimum=Decimal("0.00"),
        maximum=Decimal("100.00"),
    )
    return FacilitySettingsView(
        facility_id=candidate.facility_id,
        facility_name=name,
        facility_address=address,
        operating_hours=hours,
        hourly_rate=hourly,
        daily_max_rate=daily,
        grace_period_minutes=grace,
        ev_surcharge=surcharge,
        high_occupancy_alert=_flag(candidate.high_occupancy_alert, "High occupancy alert"),
        reservation_overstay_alert=_flag(
            candidate.reservation_overstay_alert, "Reservation overstay alert"
        ),
        space_fault_alert=_flag(candidate.space_fault_alert, "Space fault alert"),
    )


def _view(facility, settings) -> FacilitySettingsView:
    return FacilitySettingsView(
        facility_id=facility.id,
        facility_name=facility.name,
        facility_address=facility.address,
        operating_hours=facility.operating_hours,
        hourly_rate=settings.hourly_rate,
        daily_max_rate=settings.daily_max_rate,
        grace_period_minutes=settings.grace_period_minutes,
        ev_surcharge=settings.ev_surcharge,
        high_occupancy_alert=settings.high_occupancy_alert,
        reservation_overstay_alert=settings.reservation_overstay_alert,
        space_fault_alert=settings.space_fault_alert,
    )


def _merge(facility, settings, changes: FacilitySettingsUpdate) -> FacilitySettingsView:
    def pick(updated, current):
        return current if updated is None else updated

    return FacilitySettingsView(
        facility_id=facility.id,
        facility_name=pick(changes.facility_name, facility.name),
        facility_address=pick(changes.facility_address, facility.address),
        operating_hours=pick(changes.operating_hours, facility.operating_hours),
        hourly_rate=pick(changes.hourly_rate, settings.hourly_rate),
        daily_max_rate=pick(changes.daily_max_rate, settings.daily_max_rate),
        grace_period_minutes=pick(changes.grace_period_minutes, settings.grace_period_minutes),
        ev_surcharge=pick(changes.ev_surcharge, settings.ev_surcharge),
        high_occupancy_alert=pick(changes.high_occupancy_alert, settings.high_occupancy_alert),
        reservation_overstay_alert=pick(
            changes.reservation_overstay_alert, settings.reservation_overstay_alert
        ),
        space_fault_alert=pick(changes.space_fault_alert, settings.space_fault_alert),
    )


def _text(value: str, label: str, *, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be text.")
    cleaned = value.strip()
    if len(cleaned) < minimum:
        raise ValidationError(f"{label} must be at least {minimum} characters.")
    if len(cleaned) > maximum:
        raise ValidationError(f"{label} must be {maximum} characters or fewer.")
    return cleaned


def _money(value: Decimal, message: str, *, minimum: Decimal, maximum: Decimal) -> Decimal:
    amount = quantize_money(value)
    if amount < minimum or amount > maximum:
        raise ValidationError(message)
    return amount


def _flag(value: bool, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{label} must be true or false.")
    return value
