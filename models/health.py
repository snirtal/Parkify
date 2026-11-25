"""Health-check response model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class HealthStatus:
    """Represents the API health-check payload."""

    status: str
    service: str
    environment: str
    version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
