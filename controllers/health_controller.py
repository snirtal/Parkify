"""Health-check HTTP controller."""

from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify

from services.health_service import HealthService

logger = logging.getLogger("parkify.health")
health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def get_health():
    """Return API health status for local and monitoring checks."""
    settings = current_app.config["PARKIFY_SETTINGS"]
    service = HealthService(settings)
    payload = service.get_health().to_dict()
    logger.debug("health status=%s", payload["status"])
    return jsonify(payload), 200
