"""Parking-session repository.

An open session is the occupancy record for a spot. This module only reads
and stages those rows.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from models.orm import ParkingSession
from repositories.base import SqlAlchemyCrudRepository, _guarded


class ParkingSessionRepository(Protocol):
    def get(self, entity_id: str) -> ParkingSession | None: ...

    def list(
        self, *, limit: int | None = None, offset: int = 0
    ) -> Sequence[ParkingSession]: ...

    def add(self, entity: ParkingSession) -> ParkingSession: ...

    def delete(self, entity: ParkingSession) -> None: ...

    def list_active(self) -> Sequence[ParkingSession]: ...

    def get_active_for_spot(self, spot_id: str) -> ParkingSession | None: ...

    def list_for_spot(self, spot_id: str) -> Sequence[ParkingSession]: ...

    def list_for_vehicle(self, vehicle_id: str) -> Sequence[ParkingSession]: ...

    def list_overlapping_interval(
        self, start: datetime, end: datetime
    ) -> Sequence[ParkingSession]: ...


def _with_parties(statement):
    return statement.options(
        joinedload(ParkingSession.vehicle),
        joinedload(ParkingSession.spot),
    )


class SqlAlchemyParkingSessionRepository(SqlAlchemyCrudRepository[ParkingSession]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ParkingSession)

    @_guarded("list_active")
    def list_active(self) -> list[ParkingSession]:
        self.logger.debug("list_active")
        statement = _with_parties(
            select(ParkingSession)
            .where(ParkingSession.ended_at.is_(None))
            .order_by(ParkingSession.started_at, ParkingSession.id)
        )
        return list(self.session.scalars(statement).unique())

    @_guarded("get_active_for_spot")
    def get_active_for_spot(self, spot_id: str) -> ParkingSession | None:
        self.logger.debug("get_active_for_spot spot_id=%s", spot_id)
        statement = _with_parties(
            select(ParkingSession).where(
                ParkingSession.spot_id == spot_id,
                ParkingSession.ended_at.is_(None),
            )
        )
        return self.session.scalars(statement).unique().one_or_none()

    @_guarded("list_for_spot")
    def list_for_spot(self, spot_id: str) -> list[ParkingSession]:
        self.logger.debug("list_for_spot spot_id=%s", spot_id)
        statement = _with_parties(
            select(ParkingSession)
            .where(ParkingSession.spot_id == spot_id)
            .order_by(ParkingSession.started_at, ParkingSession.id)
        )
        return list(self.session.scalars(statement).unique())

    @_guarded("list_for_vehicle")
    def list_for_vehicle(self, vehicle_id: str) -> list[ParkingSession]:
        self.logger.debug("list_for_vehicle vehicle_id=%s", vehicle_id)
        statement = _with_parties(
            select(ParkingSession)
            .where(ParkingSession.vehicle_id == vehicle_id)
            .order_by(ParkingSession.started_at, ParkingSession.id)
        )
        return list(self.session.scalars(statement).unique())

    @_guarded("list_overlapping_interval")
    def list_overlapping_interval(self, start: datetime, end: datetime) -> list[ParkingSession]:
        """Return sessions that overlap the half-open interval [start, end)."""
        self.logger.debug("list_overlapping_interval")
        statement = _with_parties(
            select(ParkingSession)
            .where(
                ParkingSession.started_at < end,
                or_(
                    ParkingSession.ended_at.is_(None),
                    ParkingSession.ended_at > start,
                ),
            )
            .order_by(ParkingSession.started_at, ParkingSession.id)
        )
        return list(self.session.scalars(statement).unique())
