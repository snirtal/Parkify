"""Request parsing for controllers.

These checks reject a malformed HTTP request before a service is called.
Business rules stay in the services.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import request

from utils.errors import AppError


def json_object() -> dict:
    """Return a JSON object body, or raise a 400 error."""
    if not request.is_json:
        raise AppError("Request body must be a JSON object.", code="validation_error", status_code=400)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise AppError("Request body must be a JSON object.", code="validation_error", status_code=400)
    return payload


def identifier(value: str, label: str, *, maximum: int = 64) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum or any(char.isspace() for char in cleaned):
        raise AppError(f"{label} is not valid.", code="validation_error", status_code=400)
    return cleaned


def query_text(name: str, *, maximum: int) -> str | None:
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return None
    cleaned = raw.strip()
    if len(cleaned) > maximum:
        raise AppError(f"{name} is too long.", code="validation_error", status_code=400)
    return cleaned


def query_choice(name: str, allowed: frozenset[str] | tuple[str, ...]) -> str | None:
    value = query_text(name, maximum=32)
    if value is None:
        return None
    if value not in allowed:
        raise AppError(f"{name} is not recognized.", code="validation_error", status_code=400)
    return value


def query_int(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return default
    text = raw.strip()
    if text.startswith("-"):
        digits = text[1:]
    else:
        digits = text
    if not digits.isdigit():
        raise AppError(f"{name} must be a whole number.", code="validation_error", status_code=400)
    value = int(text)
    if value < minimum or value > maximum:
        raise AppError(
            f"{name} must be between {minimum} and {maximum}.",
            code="validation_error",
            status_code=400,
        )
    return value


def required_text(payload: dict, name: str, *, maximum: int) -> str:
    if name not in payload or payload[name] is None:
        raise AppError(f"{name} is required.", code="validation_error", status_code=400)
    return _text(payload[name], name, maximum=maximum, allow_empty=False)


def optional_text(payload: dict, name: str, *, maximum: int) -> str | None:
    if name not in payload:
        return None
    if payload[name] is None:
        raise AppError(f"{name} cannot be null.", code="validation_error", status_code=400)
    cleaned = _text(payload[name], name, maximum=maximum, allow_empty=True)
    return cleaned or None


def required_timestamp(payload: dict, name: str) -> datetime:
    if name not in payload or payload[name] is None:
        raise AppError(f"{name} is required.", code="validation_error", status_code=400)
    return parse_timestamp(payload[name], name)


def optional_timestamp(payload: dict, name: str) -> datetime | None:
    if name not in payload:
        return None
    if payload[name] is None:
        raise AppError(f"{name} cannot be null.", code="validation_error", status_code=400)
    return parse_timestamp(payload[name], name)


def query_timestamp(name: str, *, required: bool) -> datetime | None:
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        if required:
            raise AppError(f"{name} is required.", code="validation_error", status_code=400)
        return None
    return parse_timestamp(raw, name)


def optional_money(payload: dict, name: str) -> Decimal | None:
    if name not in payload:
        return None
    if payload[name] is None:
        raise AppError(f"{name} cannot be null.", code="validation_error", status_code=400)
    return parse_money(payload[name], name)


def optional_whole_number(payload: dict, name: str) -> int | None:
    if name not in payload:
        return None
    if payload[name] is None:
        raise AppError(f"{name} cannot be null.", code="validation_error", status_code=400)
    value = payload[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise AppError(f"{name} must be a whole number.", code="validation_error", status_code=400)
    return value


def optional_bool(payload: dict, name: str) -> bool | None:
    if name not in payload:
        return None
    if payload[name] is None:
        raise AppError(f"{name} cannot be null.", code="validation_error", status_code=400)
    if not isinstance(payload[name], bool):
        raise AppError(f"{name} must be true or false.", code="validation_error", status_code=400)
    return payload[name]


def parse_timestamp(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise AppError(
            f"{name} must be a facility-local timestamp.",
            code="validation_error",
            status_code=400,
        )
    text = value.strip()
    if not text or "Z" in text or "+" in text or _has_negative_offset(text):
        raise AppError(
            "Timestamps must be facility-local values without a time zone.",
            code="validation_error",
            status_code=400,
        )
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AppError(
            f"{name} must be a facility-local timestamp.",
            code="validation_error",
            status_code=400,
        ) from exc
    if parsed.tzinfo is not None:
        raise AppError(
            "Timestamps must be facility-local values without a time zone.",
            code="validation_error",
            status_code=400,
        )
    return parsed


def parse_money(value: object, name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (int, str)):
        raise AppError(
            f"{name} must be a decimal string such as \"4.20\".",
            code="validation_error",
            status_code=400,
        )
    text = str(value) if isinstance(value, int) else value.strip()
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise AppError(
            f"{name} must be a decimal string such as \"4.20\".",
            code="validation_error",
            status_code=400,
        ) from exc
    if not amount.is_finite():
        raise AppError(
            f"{name} must be a decimal string such as \"4.20\".",
            code="validation_error",
            status_code=400,
        )
    return amount


def _text(value: object, name: str, *, maximum: int, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise AppError(f"{name} must be text.", code="validation_error", status_code=400)
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise AppError(f"{name} is required.", code="validation_error", status_code=400)
    if len(cleaned) > maximum:
        raise AppError(f"{name} is too long.", code="validation_error", status_code=400)
    return cleaned


def _has_negative_offset(text: str) -> bool:
    separator = "T" if "T" in text else " "
    if separator not in text:
        return False
    return "-" in text.split(separator, 1)[1]
