"""Centralized application errors and Flask error handlers."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("parkify.errors")


class AppError(Exception):
    """Base application error with a stable API error code and HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


def error_payload(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a consistent JSON error body."""
    payload: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return payload


def register_error_handlers(app: Flask) -> None:
    """Register centralized JSON error handlers on the Flask app."""

    @app.errorhandler(AppError)
    def handle_app_error(exc: AppError):
        logger.warning("Application error [%s]: %s", exc.code, exc.message)
        return (
            jsonify(
                error_payload(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details or None,
                )
            ),
            exc.status_code,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        code = (exc.name or "http_error").lower().replace(" ", "_")
        message = exc.description or exc.name or "Request failed"
        logger.info("HTTP error %s: %s", exc.code, message)
        return jsonify(error_payload(code=code, message=message)), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return (
            jsonify(
                error_payload(
                    code="internal_server_error",
                    message="An unexpected error occurred.",
                )
            ),
            500,
        )
