"""Parkify Flask application factory and local entrypoint."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from config.database import init_database
from config.settings import Settings, get_settings
from controllers import register_api
from services.auth import LoginRateLimiter
from utils.errors import register_error_handlers
from utils.logging_setup import setup_logging
from utils.request_logging import register_request_logging


def create_app(environment: str | None = None) -> Flask:
    """
    Create and configure the Flask application.

    Uses a clean application factory so tests and future WSGI servers
    can construct isolated app instances.
    """
    settings: Settings = get_settings(environment)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["DEBUG"] = settings.debug
    app.config["PARKIFY_SETTINGS"] = settings

    setup_logging(settings)
    init_database(app)
    app.extensions["login_rate_limiter"] = LoginRateLimiter(
        max_attempts=settings.login_max_attempts,
        window_seconds=settings.login_window_seconds,
    )
    register_error_handlers(app)
    register_request_logging(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": settings.cors_origins}},
        supports_credentials=False,
    )

    register_api(app)
    return app


app = create_app()


if __name__ == "__main__":
    settings = app.config["PARKIFY_SETTINGS"]
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
