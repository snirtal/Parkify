"""Parking-zone repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orm import ParkingZone
from repositories.base import SqlAlchemyCrudRepository, _guarded


class ZoneRepository(Protocol):
    def get(self, entity_id: str) -> ParkingZone | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[ParkingZone]: ...

    def add(self, entity: ParkingZone) -> ParkingZone: ...

    def delete(self, entity: ParkingZone) -> None: ...

    def list_for_floor(self, floor_id: str) -> Sequence[ParkingZone]: ...

    def get_by_code(self, code: str) -> ParkingZone | None: ...


class SqlAlchemyZoneRepository(SqlAlchemyCrudRepository[ParkingZone]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ParkingZone)

    @_guarded("list_for_floor")
    def list_for_floor(self, floor_id: str) -> list[ParkingZone]:
        self.logger.debug("list_for_floor floor_id=%s", floor_id)
        statement = (
            select(ParkingZone)
            .where(ParkingZone.floor_id == floor_id)
            .order_by(ParkingZone.code)
        )
        return list(self.session.scalars(statement))

    @_guarded("get_by_code")
    def get_by_code(self, code: str) -> ParkingZone | None:
        self.logger.debug("get_by_code code=%s", code)
        statement = select(ParkingZone).where(ParkingZone.code == code)
        return self.session.scalar(statement)
