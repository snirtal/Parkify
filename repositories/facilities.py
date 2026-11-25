"""Facility and facility-settings repositories."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.orm import Facility, FacilitySettings, Floor
from repositories.base import SqlAlchemyCrudRepository, _guarded


class FacilityRepository(Protocol):
    """Facility lookup. Settings and floors are loaded with the facility."""

    def get(self, entity_id: str) -> Facility | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[Facility]: ...

    def add(self, entity: Facility) -> Facility: ...

    def delete(self, entity: Facility) -> None: ...

    def get_with_children(self, facility_id: str) -> Facility | None: ...


class FacilitySettingsRepository(Protocol):
    """Retrieval and field updates for one facility's settings row."""

    def get(self, entity_id: str) -> FacilitySettings | None: ...

    def list(
        self, *, limit: int | None = None, offset: int = 0
    ) -> Sequence[FacilitySettings]: ...

    def add(self, entity: FacilitySettings) -> FacilitySettings: ...

    def delete(self, entity: FacilitySettings) -> None: ...

    def get_for_facility(self, facility_id: str) -> FacilitySettings | None: ...

    def apply_changes(
        self,
        settings: FacilitySettings,
        *,
        hourly_rate: Decimal | None = None,
        daily_max_rate: Decimal | None = None,
        grace_period_minutes: int | None = None,
        ev_surcharge: Decimal | None = None,
        high_occupancy_alert: bool | None = None,
        reservation_overstay_alert: bool | None = None,
        space_fault_alert: bool | None = None,
    ) -> FacilitySettings: ...


class SqlAlchemyFacilityRepository(SqlAlchemyCrudRepository[Facility]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Facility)

    @_guarded("get_with_children")
    def get_with_children(self, facility_id: str) -> Facility | None:
        self.logger.debug("get_with_children id=%s", facility_id)
        statement = (
            select(Facility)
            .where(Facility.id == facility_id)
            .options(
                selectinload(Facility.settings),
                selectinload(Facility.floors).selectinload(Floor.zones),
            )
        )
        return self.session.scalar(statement)


class SqlAlchemyFacilitySettingsRepository(SqlAlchemyCrudRepository[FacilitySettings]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, FacilitySettings)

    @_guarded("get_for_facility")
    def get_for_facility(self, facility_id: str) -> FacilitySettings | None:
        self.logger.debug("get_for_facility facility_id=%s", facility_id)
        statement = select(FacilitySettings).where(FacilitySettings.facility_id == facility_id)
        return self.session.scalar(statement)

    def apply_changes(
        self,
        settings: FacilitySettings,
        *,
        hourly_rate: Decimal | None = None,
        daily_max_rate: Decimal | None = None,
        grace_period_minutes: int | None = None,
        ev_surcharge: Decimal | None = None,
        high_occupancy_alert: bool | None = None,
        reservation_overstay_alert: bool | None = None,
        space_fault_alert: bool | None = None,
    ) -> FacilitySettings:
        """Assign supplied columns. Database constraints run when the caller flushes."""
        changes = {
            "hourly_rate": hourly_rate,
            "daily_max_rate": daily_max_rate,
            "grace_period_minutes": grace_period_minutes,
            "ev_surcharge": ev_surcharge,
            "high_occupancy_alert": high_occupancy_alert,
            "reservation_overstay_alert": reservation_overstay_alert,
            "space_fault_alert": space_fault_alert,
        }
        for name, value in changes.items():
            if value is not None:
                setattr(settings, name, value)
        self.logger.debug("apply_changes id=%s", settings.id)
        return settings
