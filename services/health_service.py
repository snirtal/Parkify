"""Health-check business logic."""

from __future__ import annotations

from config.settings import Settings
from models.health import HealthStatus

API_VERSION = "0.1.0"


class HealthService:
    """Builds the API health status from runtime settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_health(self) -> HealthStatus:
        """Return the current service health snapshot."""
        return HealthStatus(
            status="ok",
            service=self._settings.app_name,
            environment=self._settings.environment,
            version=API_VERSION,
        )
