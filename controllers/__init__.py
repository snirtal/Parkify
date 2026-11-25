"""HTTP controllers for Parkify API routes."""

from flask import Flask

from controllers.analytics_controller import analytics_bp
from controllers.dashboard_controller import dashboard_bp
from controllers.gate_controller import gate_bp
from controllers.health_controller import health_bp
from controllers.parking_controller import parking_bp
from controllers.pricing_controller import pricing_bp
from controllers.reservations_controller import reservations_bp
from controllers.sessions_controller import sessions_bp
from controllers.settings_controller import settings_bp

__all__ = [
    "analytics_bp",
    "dashboard_bp",
    "gate_bp",
    "health_bp",
    "parking_bp",
    "pricing_bp",
    "register_api",
    "reservations_bp",
    "sessions_bp",
    "settings_bp",
]


def register_api(app: Flask) -> None:
    """Attach every API blueprint. Routes stay under /api."""
    app.register_blueprint(health_bp)
    app.register_blueprint(parking_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(gate_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(pricing_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
