"""JSON conversion for service results.

Decimal values are strings so two-decimal money and one-decimal occupancy
percentages keep their scale. Timestamps stay facility-local and have no
time zone suffix.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


def dump(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if is_dataclass(value) and not isinstance(value, type):
        return {key: dump(item) for key, item in asdict(value).items()}
    if isinstance(value, (list, tuple)):
        return [dump(item) for item in value]
    if isinstance(value, dict):
        return {key: dump(item) for key, item in value.items()}
    return value
