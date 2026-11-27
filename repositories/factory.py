"""Build the PostgreSQL repositories for one caller-owned session."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from repositories.auth_sessions import AuthSessionRepository, SqlAlchemyAuthSessionRepository
from repositories.facilities import (
    FacilityRepository,
    FacilitySettingsRepository,
    SqlAlchemyFacilityRepository,
    SqlAlchemyFacilitySettingsRepository,
)
from repositories.floors import FloorRepository, SqlAlchemyFloorRepository
from repositories.gate_activities import GateActivityRepository, SqlAlchemyGateActivityRepository
from repositories.reservations import ReservationRepository, SqlAlchemyReservationRepository
from repositories.reservation_requests import (
    ReservationRequestRepository,
    SqlAlchemyReservationRequestRepository,
)
from repositories.sessions import ParkingSessionRepository, SqlAlchemyParkingSessionRepository
from repositories.spots import ParkingSpotRepository, SqlAlchemyParkingSpotRepository
from repositories.users import SqlAlchemyUserRepository, UserRepository
from repositories.vehicles import VehicleRepository, SqlAlchemyVehicleRepository
from repositories.zones import SqlAlchemyZoneRepository, ZoneRepository


@dataclass(frozen=True)
class Repositories:
    """The data-access objects for a single transaction."""

    facilities: FacilityRepository
    settings: FacilitySettingsRepository
    floors: FloorRepository
    zones: ZoneRepository
    spots: ParkingSpotRepository
    vehicles: VehicleRepository
    sessions: ParkingSessionRepository
    reservations: ReservationRepository
    reservation_requests: ReservationRequestRepository
    gate_activities: GateActivityRepository
    users: UserRepository
    auth_sessions: AuthSessionRepository


def build_repositories(session: Session) -> Repositories:
    """Inject one SQLAlchemy session into every repository."""
    return Repositories(
        facilities=SqlAlchemyFacilityRepository(session),
        settings=SqlAlchemyFacilitySettingsRepository(session),
        floors=SqlAlchemyFloorRepository(session),
        zones=SqlAlchemyZoneRepository(session),
        spots=SqlAlchemyParkingSpotRepository(session),
        vehicles=SqlAlchemyVehicleRepository(session),
        sessions=SqlAlchemyParkingSessionRepository(session),
        reservations=SqlAlchemyReservationRepository(session),
        reservation_requests=SqlAlchemyReservationRequestRepository(session),
        gate_activities=SqlAlchemyGateActivityRepository(session),
        users=SqlAlchemyUserRepository(session),
        auth_sessions=SqlAlchemyAuthSessionRepository(session),
    )
