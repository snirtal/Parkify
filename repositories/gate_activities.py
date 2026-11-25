"""Gate-activity repository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models.orm import GateActivity
from repositories.base import Page, SqlAlchemyCrudRepository, _guarded, _validate_page


class GateActivityRepository(Protocol):
    def get(self, entity_id: str) -> GateActivity | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[GateActivity]: ...

    def add(self, entity: GateActivity) -> GateActivity: ...

    def delete(self, entity: GateActivity) -> None: ...

    def list_page(
        self,
        *,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[GateActivity]: ...


class SqlAlchemyGateActivityRepository(SqlAlchemyCrudRepository[GateActivity]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, GateActivity)

    @_guarded("list_page")
    def list_page(
        self,
        *,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page[GateActivity]:
        """Return a page of gate events, newest first.

        `occurred_from` is inclusive and `occurred_to` is exclusive.
        """
        _validate_page(limit, offset)
        self.logger.debug("list_page limit=%s offset=%s", limit, offset)
        filters = []
        if spot_id is not None:
            filters.append(GateActivity.spot_id == spot_id)
        if vehicle_id is not None:
            filters.append(GateActivity.vehicle_id == vehicle_id)
        if direction is not None:
            filters.append(GateActivity.direction == direction)
        if status is not None:
            filters.append(GateActivity.status == status)
        if occurred_from is not None:
            filters.append(GateActivity.occurred_at >= occurred_from)
        if occurred_to is not None:
            filters.append(GateActivity.occurred_at < occurred_to)

        total = self.session.scalar(
            select(func.count()).select_from(GateActivity).where(*filters)
        )
        statement = (
            select(GateActivity)
            .where(*filters)
            .order_by(GateActivity.occurred_at.desc(), GateActivity.id.desc())
            .limit(limit)
            .offset(offset)
            .options(joinedload(GateActivity.vehicle), joinedload(GateActivity.spot))
        )
        items = list(self.session.scalars(statement).unique())
        return Page(items=items, total=int(total or 0), limit=limit, offset=offset)
