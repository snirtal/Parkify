"""The service objects used by the current request."""

from __future__ import annotations

from flask import current_app

from services.factory import build_services
from services.unit_of_work import unit_of_work_factory
from utils.errors import AppError


def current_services():
    """Build services for this request.

    Tests can install `service_factory` so the request uses the rolled-back
    database session. Otherwise each operation opens its own unit of work.
    """
    override = current_app.extensions.get("service_factory")
    if override is not None:
        return override()
    session_factory = current_app.extensions.get("db_session_factory")
    if session_factory is None:
        raise AppError(
            "Database is not configured.",
            code="database_not_configured",
            status_code=500,
        )
    return build_services(unit_of_work_factory(session_factory))
