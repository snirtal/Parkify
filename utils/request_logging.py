"""Request logging that records the route, not the payload."""

from __future__ import annotations

import logging
from time import perf_counter

from flask import Flask, g, request

logger = logging.getLogger("parkify.http")


def register_request_logging(app: Flask) -> None:
    """Log method, path, status, and duration for every response.

    Query strings and bodies are omitted. They can contain license plates
    and are not needed to operate the API.
    """

    @app.before_request
    def _remember_start() -> None:
        g.http_started = perf_counter()

    @app.after_request
    def _log_response(response):
        started = g.get("http_started")
        elapsed_ms = 0 if started is None else int((perf_counter() - started) * 1000)
        logger.info(
            "method=%s path=%s status=%s duration_ms=%s",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response
