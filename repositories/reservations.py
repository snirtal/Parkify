"""Reservation repository.

Overlap results are matching rows. Deciding whether a booking is allowed
belongs to a later service.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from models.orm import Reservation
from repositories.base import SqlAlchemyCrudRepository, _guarded


class ReservationRepository(Protocol):
    def get(self, entity_id: str) -> Reservation | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[Reservation]: ...

    def add(self, entity: Reservation) -> Reservation: ...

    def delete(self, entity: Reservation) -> None: ...

    def list_filtered(
        self,
        *,
        status: str | None = None,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
        include_cancelled: bool = True,
    ) -> Sequence[Reservation]: ...

    def list_overlapping(
        self,
        spot_id: str,
        starts_at: datetime,
        ends_at: datetime,
        *,
        include_cancelled: bool = False,
    ) -> Sequence[Reservation]: ...

    def list_covering(
        self,
        moment: datetime,
        *,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
    ) -> Sequence[Reservation]: ...


def _filtered_statement(
    *,
    status: str | None = None,
    spot_id: str | None = None,
    vehicle_id: str | None = None,
    range_start: datetime | None = None,
    range_end: datetime | None = None,
    include_cancelled: bool = True,
) -> Select[tuple[Reservation]]:
    statement = select(Reservation)
    if status is not None:
        statement = statement.where(Reservation.status == status)
    elif not include_cancelled:
        statement = statement.where(Reservation.status != "Cancelled")
    if spot_id is not None:
        statement = statement.where(Reservation.spot_id == spot_id)
    if vehicle_id is not None:
        statement = statement.where(Reservation.vehicle_id == vehicle_id)
    if range_start is not None:
        statement = statement.where(Reservation.ends_at > range_start)
    if range_end is not None:
        statement = statement.where(Reservation.starts_at < range_end)
    return (
        statement.order_by(Reservation.starts_at, Reservation.id)
        .options(joinedload(Reservation.vehicle), joinedload(Reservation.spot))
    )


class SqlAlchemyReservationRepository(SqlAlchemyCrudRepository[Reservation]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Reservation)

    @_guarded("list_filtered")
    def list_filtered(
        self,
        *,
        status: str | None = None,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
        include_cancelled: bool = True,
    ) -> list[Reservation]:
        self.logger.debug("list_filtered status=%s spot_id=%s", status, spot_id)
        statement = _filtered_statement(
            status=status,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            range_start=range_start,
            range_end=range_end,
            include_cancelled=include_cancelled,
        )
        return list(self.session.scalars(statement).unique())

    @_guarded("list_overlapping")
    def list_overlapping(
        self,
        spot_id: str,
        starts_at: datetime,
        ends_at: datetime,
        *,
        include_cancelled: bool = False,
    ) -> list[Reservation]:
        """Return reservations on this spot whose window intersects the given window."""
        self.logger.debug("list_overlapping spot_id=%s", spot_id)
        return self.list_filtered(
            spot_id=spot_id,
            range_start=starts_at,
            range_end=ends_at,
            include_cancelled=include_cancelled,
        )

    @_guarded("list_covering")
    def list_covering(
        self,
        moment: datetime,
        *,
        spot_id: str | None = None,
        vehicle_id: str | None = None,
    ) -> list[Reservation]:
        """Return non-cancelled reservations whose window contains `moment`."""
        self.logger.debug("list_covering spot_id=%s", spot_id)
        statement = select(Reservation).where(
            Reservation.status != "Cancelled",
            Reservation.starts_at <= moment,
            Reservation.ends_at > moment,
        )
        if spot_id is not None:
            statement = statement.where(Reservation.spot_id == spot_id)
        if vehicle_id is not None:
            statement = statement.where(Reservation.vehicle_id == vehicle_id)
        statement = statement.order_by(Reservation.starts_at, Reservation.id).options(
            joinedload(Reservation.vehicle),
            joinedload(Reservation.spot),
        )
        return list(self.session.scalars(statement).unique())
