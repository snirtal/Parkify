"""Floor repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.orm import Floor
from repositories.base import SqlAlchemyCrudRepository, _guarded


class FloorRepository(Protocol):
    def get(self, entity_id: str) -> Floor | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[Floor]: ...

    def add(self, entity: Floor) -> Floor: ...

    def delete(self, entity: Floor) -> None: ...

    def list_for_facility(self, facility_id: str) -> Sequence[Floor]: ...

    def get_by_code(self, facility_id: str, code: str) -> Floor | None: ...


class SqlAlchemyFloorRepository(SqlAlchemyCrudRepository[Floor]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Floor)

    @_guarded("list_for_facility")
    def list_for_facility(self, facility_id: str) -> list[Floor]:
        self.logger.debug("list_for_facility facility_id=%s", facility_id)
        statement = (
            select(Floor)
            .where(Floor.facility_id == facility_id)
            .order_by(Floor.level_index)
            .options(selectinload(Floor.zones))
        )
        return list(self.session.scalars(statement))

    @_guarded("get_by_code")
    def get_by_code(self, facility_id: str, code: str) -> Floor | None:
        self.logger.debug("get_by_code facility_id=%s code=%s", facility_id, code)
        statement = select(Floor).where(Floor.facility_id == facility_id, Floor.code == code)
        return self.session.scalar(statement)
