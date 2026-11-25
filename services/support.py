"""Shared service helpers: clock, ids, and the transaction runner."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol, TypeVar
from uuid import uuid4

from models.orm import Facility, Vehicle

from repositories.exceptions import RepositoryConflict
from services.exceptions import ConflictError, ConstraintConflict, NotFoundError, ValidationError

T = TypeVar("T")
logger = logging.getLogger("parkify.service")


class Clock(Protocol):
    """Facility-local time used by business rules."""

    def now(self, facility: Facility) -> datetime: ...


class FacilityClock:
    """The simulated clock stored on the facility, not the server wall clock."""

    def now(self, facility: Facility) -> datetime:
        return datetime.combine(facility.simulated_date, facility.simulated_time)


class FixedClock:
    """A caller-supplied instant. Tests use this to make time deterministic."""

    def __init__(self, moment: datetime) -> None:
        if moment.tzinfo is not None:
            raise ValidationError(
                "The facility clock must be a facility-local value without a time zone."
            )
        self._moment = moment

    def now(self, facility: Facility) -> datetime:
        return self._moment


class IdFactory(Protocol):
    def __call__(self, prefix: str) -> str: ...


def default_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def run_in_transaction(uow_factory: Callable[[], Any], work: Callable[[Any], T]) -> T:
    """Run one business operation and commit it, or roll it back on failure."""
    with uow_factory() as uow:
        try:
            result = work(uow)
            uow.commit()
            return result
        except ConstraintConflict as exc:
            uow.rollback()
            raise ConflictError(
                "The operation conflicts with existing data.",
                code="concurrent_update",
            ) from exc
        except RepositoryConflict as exc:
            uow.rollback()
            raise ConflictError(
                "The operation could not be completed because of a concurrent update.",
                code="concurrent_update",
            ) from exc
        except Exception as exc:
            uow.rollback()
            logger.info("rolled back a service transaction (%s)", type(exc).__name__)
            raise


def require_facility(repos, facility_id: str) -> Facility:
    facility = repos.facilities.get(facility_id)
    if facility is None:
        raise NotFoundError("Facility was not found.")
    return facility


def facility_moment(clock: Clock, facility: Facility, at: datetime | None) -> datetime:
    if at is None:
        moment = clock.now(facility)
    else:
        moment = at
    if moment.tzinfo is not None:
        raise ValidationError(
            "Timestamps must be facility-local values without a time zone."
        )
    return moment


def clean_plate(plate_number: str) -> str:
    plate = plate_number.strip()
    alphanumeric = [char for char in plate if char.isalnum()]
    if len(alphanumeric) < 2 or len(plate) > 16:
        raise ValidationError("Enter a vehicle license plate of at least 2 characters.")
    return plate


def require_settings(repos, facility_id: str):
    settings = repos.settings.get_for_facility(facility_id)
    if settings is None:
        raise NotFoundError("Facility settings were not found.")
    return settings


def lock_vehicle(repos, vehicle: Vehicle) -> Vehicle:
    locked = repos.vehicles.get_for_update(vehicle.id)
    if locked is None:
        raise NotFoundError("Vehicle was not found.")
    return locked
