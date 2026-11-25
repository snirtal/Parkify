"""Centralized logging configuration."""

from __future__ import annotations

import logging
from logging import Logger

from config.settings import Settings


def setup_logging(settings: Settings) -> Logger:
    """
    Configure application-wide logging.

    Uses Python's logging module with a consistent format and level
    derived from centralized settings.
    """
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(settings.log_level)

    handler = logging.StreamHandler()
    handler.setLevel(settings.log_level)
    handler.setFormatter(logging.Formatter(settings.log_format))
    root_logger.addHandler(handler)

    # Keep noisy third-party loggers quieter in production.
    logging.getLogger("werkzeug").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )

    app_logger = logging.getLogger("parkify")
    app_logger.setLevel(settings.log_level)
    app_logger.debug(
        "Logging initialized (env=%s, level=%s)",
        settings.environment,
        settings.log_level,
    )
    return app_logger
