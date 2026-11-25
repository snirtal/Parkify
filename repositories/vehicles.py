"""Vehicle repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orm import Vehicle
from repositories.base import SqlAlchemyCrudRepository, _guarded


class VehicleRepository(Protocol):
    def get(self, entity_id: str) -> Vehicle | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[Vehicle]: ...

    def add(self, entity: Vehicle) -> Vehicle: ...

    def delete(self, entity: Vehicle) -> None: ...

    def get_by_plate(self, plate_number: str) -> Vehicle | None: ...

    def get_for_update(self, entity_id: str) -> Vehicle | None: ...


class SqlAlchemyVehicleRepository(SqlAlchemyCrudRepository[Vehicle]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Vehicle)

    @_guarded("get_by_plate")
    def get_by_plate(self, plate_number: str) -> Vehicle | None:
        self.logger.debug("get_by_plate")
        statement = select(Vehicle).where(Vehicle.plate_number == plate_number)
        return self.session.scalar(statement)
