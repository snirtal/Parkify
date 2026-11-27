"""Request logging that records the route, not the payload."""

from __future__ import annotations

import logging
from time import perf_counter

from flask import Flask, g, request

from utils.request_context import bind_request_id, current_request_id, reset_request_id

logger = logging.getLogger("parkify.http")
REQUEST_ID_HEADER = "X-Request-ID"


def register_request_logging(app: Flask) -> None:
    """Log method, path, status, and duration for every response.

    Query strings and bodies are omitted. They can contain license plates
    and are not needed to operate the API. The request id is also returned
    on the response.
    """

    @app.before_request
    def _remember_start() -> None:
        g.http_started = perf_counter()
        g.request_id_token = bind_request_id(request.headers.get(REQUEST_ID_HEADER))

    @app.after_request
    def _log_response(response):
        started = g.get("http_started")
        elapsed_ms = 0 if started is None else int((perf_counter() - started) * 1000)
        request_id = current_request_id()
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.teardown_request
    def _clear_request_id(_error: BaseException | None) -> None:
        token = g.pop("request_id_token", None)
        if token is not None:
            reset_request_id(token)
