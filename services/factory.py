"""Wire the services to one unit-of-work factory and one clock."""

from __future__ import annotations

from dataclasses import dataclass

from services.analytics import AnalyticsService
from services.dashboard import DashboardService
from services.gate import GateService
from services.parking import ParkingService
from services.pricing import PricingService
from services.reservations import ReservationService
from services.sessions import ParkingSessionService
from services.settings import SettingsService
from services.passwords import Argon2PasswordHasher, PasswordHasherProtocol
from services.support import Clock, FacilityClock, IdFactory, default_id
from services.users import UserService


@dataclass(frozen=True)
class Services:
    """The business operations for one application."""

    parking: ParkingService
    sessions: ParkingSessionService
    reservations: ReservationService
    pricing: PricingService
    gate: GateService
    dashboard: DashboardService
    analytics: AnalyticsService
    settings: SettingsService
    users: UserService


def build_services(
    uow_factory,
    *,
    clock: Clock | None = None,
    ids: IdFactory | None = None,
    passwords: PasswordHasherProtocol | None = None,
    password_min_length: int | None = None,
) -> Services:
    """Inject the transaction factory, clock, and id generator into every service."""
    from config.settings import get_settings

    resolved_clock = clock or FacilityClock()
    resolved_ids = ids or default_id
    if passwords is None or password_min_length is None:
        settings = get_settings()
        passwords = passwords or Argon2PasswordHasher.from_settings(settings)
        if password_min_length is None:
            password_min_length = settings.password_min_length
    pricing = PricingService()
    sessions = ParkingSessionService(uow_factory, resolved_clock, resolved_ids, pricing)
    return Services(
        parking=ParkingService(uow_factory, resolved_clock),
        sessions=sessions,
        reservations=ReservationService(uow_factory, resolved_clock, resolved_ids),
        pricing=pricing,
        gate=GateService(sessions, uow_factory, resolved_clock),
        dashboard=DashboardService(uow_factory, resolved_clock),
        analytics=AnalyticsService(uow_factory, resolved_clock),
        settings=SettingsService(uow_factory),
        users=UserService(
            uow_factory,
            resolved_ids,
            passwords,
            password_min_length=password_min_length,
        ),
    )
