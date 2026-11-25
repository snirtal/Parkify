"""Parking-spot repository.

Spot occupancy is not stored. Sessions, reservations, and maintenance_reason
remain the records that describe how a spot is being used.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.orm import ParkingSpot
from repositories.base import SqlAlchemyCrudRepository, _guarded


class ParkingSpotRepository(Protocol):
    def get(self, entity_id: str) -> ParkingSpot | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[ParkingSpot]: ...

    def add(self, entity: ParkingSpot) -> ParkingSpot: ...

    def delete(self, entity: ParkingSpot) -> None: ...

    def get_by_code(self, code: str) -> ParkingSpot | None: ...

    def list_for_floor(self, floor_id: str) -> Sequence[ParkingSpot]: ...

    def list_for_zone(self, zone_id: str) -> Sequence[ParkingSpot]: ...


class SqlAlchemyParkingSpotRepository(SqlAlchemyCrudRepository[ParkingSpot]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ParkingSpot)

    @_guarded("get_by_code")
    def get_by_code(self, code: str) -> ParkingSpot | None:
        self.logger.debug("get_by_code code=%s", code)
        statement = (
            select(ParkingSpot)
            .where(ParkingSpot.code == code)
            .options(joinedload(ParkingSpot.zone), joinedload(ParkingSpot.floor))
        )
        return self.session.scalars(statement).unique().one_or_none()

    @_guarded("list_for_floor")
    def list_for_floor(self, floor_id: str) -> list[ParkingSpot]:
        self.logger.debug("list_for_floor floor_id=%s", floor_id)
        statement = (
            select(ParkingSpot)
            .where(ParkingSpot.floor_id == floor_id)
            .order_by(ParkingSpot.row, ParkingSpot.slot_index)
            .options(joinedload(ParkingSpot.zone))
        )
        return list(self.session.scalars(statement).unique())

    @_guarded("list_for_zone")
    def list_for_zone(self, zone_id: str) -> list[ParkingSpot]:
        self.logger.debug("list_for_zone zone_id=%s", zone_id)
        statement = (
            select(ParkingSpot)
            .where(ParkingSpot.zone_id == zone_id)
            .order_by(ParkingSpot.slot_index)
            .options(joinedload(ParkingSpot.floor))
        )
        return list(self.session.scalars(statement).unique())
