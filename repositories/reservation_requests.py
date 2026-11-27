"""Customer reservation requests. A pending row does not hold a parking spot."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models.orm import Reservation, ReservationRequest
from repositories.base import SqlAlchemyCrudRepository, _guarded


class ReservationRequestRepository(Protocol):
    def get(self, entity_id: str) -> ReservationRequest | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[ReservationRequest]: ...

    def add(self, entity: ReservationRequest) -> ReservationRequest: ...

    def delete(self, entity: ReservationRequest) -> None: ...

    def get_for_update(self, entity_id: str) -> ReservationRequest | None: ...

    def list_for_facility(self, facility_id: str) -> Sequence[ReservationRequest]: ...

    def pending_for_vehicle(self, facility_id: str, vehicle_id: str) -> ReservationRequest | None: ...

    def count_pending(self, facility_id: str) -> int: ...


def _loaded():
    return (
        joinedload(ReservationRequest.vehicle),
        joinedload(ReservationRequest.reservation).joinedload(Reservation.spot),
    )


class SqlAlchemyReservationRequestRepository(SqlAlchemyCrudRepository[ReservationRequest]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ReservationRequest)

    @_guarded("list_for_facility")
    def list_for_facility(self, facility_id: str) -> list[ReservationRequest]:
        self.logger.debug("list_for_facility facility_id=%s", facility_id)
        statement = (
            select(ReservationRequest)
            .where(ReservationRequest.facility_id == facility_id)
            .order_by(ReservationRequest.created_at.desc(), ReservationRequest.id)
            .options(*_loaded())
        )
        return list(self.session.scalars(statement).unique())

    @_guarded("pending_for_vehicle")
    def pending_for_vehicle(self, facility_id: str, vehicle_id: str) -> ReservationRequest | None:
        self.logger.debug("pending_for_vehicle facility_id=%s", facility_id)
        statement = (
            select(ReservationRequest)
            .where(
                ReservationRequest.facility_id == facility_id,
                ReservationRequest.vehicle_id == vehicle_id,
                ReservationRequest.status == "Pending",
            )
            .options(*_loaded())
        )
        return self.session.scalars(statement).unique().one_or_none()

    @_guarded("count_pending")
    def count_pending(self, facility_id: str) -> int:
        self.logger.debug("count_pending facility_id=%s", facility_id)
        statement = (
            select(func.count())
            .select_from(ReservationRequest)
            .where(
                ReservationRequest.facility_id == facility_id,
                ReservationRequest.status == "Pending",
            )
        )
        return int(self.session.scalar(statement) or 0)
