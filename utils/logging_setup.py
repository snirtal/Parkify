"""Centralized logging configuration."""

from __future__ import annotations

import logging
import re
from logging import Logger

from config.settings import Settings

_URL = re.compile(
    r"(?i)\b(?:postgres(?:ql)?(?:\+\w+)?|mysql|mongodb(?:\+srv)?|redis|amqp|https?)://\S+"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[=:]\s*\S+"
)


def redact(text: str) -> str:
    """Remove connection strings and secret assignments from a log line."""
    redacted = _URL.sub("[redacted-url]", text)
    return _SECRET_ASSIGNMENT.sub(r"\1=[redacted]", redacted)


class RedactingFormatter(logging.Formatter):
    """Format a record, then strip secrets from the finished line."""

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup_logging(settings: Settings) -> Logger:
    """
    Configure application-wide logging.

    Uses Python's logging module with a consistent format and level
    derived from centralized settings.
    """
    from utils.request_context import install_request_id_factory

    install_request_id_factory()
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(settings.log_level)

    handler = logging.StreamHandler()
    handler.setLevel(settings.log_level)
    handler.setFormatter(RedactingFormatter(settings.log_format))
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
