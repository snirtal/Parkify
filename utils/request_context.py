"""Request id carried on log records for the current HTTP request."""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar, Token
from uuid import uuid4

_request_id: ContextVar[str] = ContextVar("parkify_request_id", default="-")
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_factory_installed = False


def current_request_id() -> str:
    return _request_id.get()


def bind_request_id(requested: str | None) -> Token[str]:
    """Use a safe caller-supplied id, or create a new one."""
    if requested and _SAFE_REQUEST_ID.fullmatch(requested):
        chosen = requested
    else:
        chosen = uuid4().hex
    return _request_id.set(chosen)


def reset_request_id(token: Token[str]) -> None:
    _request_id.reset(token)


def install_request_id_factory() -> None:
    """Stamp every log record with the active request id."""
    global _factory_installed
    if _factory_installed:
        return
    previous = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        record.request_id = current_request_id()
        return record

    logging.setLogRecordFactory(factory)
    _factory_installed = True
