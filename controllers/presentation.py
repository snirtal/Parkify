"""Remove financial fields from occupancy payloads.

Employees can read availability. Rates, caps, surcharges, and quotes stay
on responses only when the caller has pricing permission.
"""

from __future__ import annotations

FINANCIAL_KEYS = frozenset(
    {
        "hourly_rate",
        "daily_max_rate",
        "ev_surcharge",
        "amount",
        "daily_maximum",
        "quote",
    }
)


def omit_financial_fields(payload: object) -> object:
    """Drop financial keys from nested dictionaries and lists."""
    if isinstance(payload, dict):
        return {
            key: omit_financial_fields(value)
            for key, value in payload.items()
            if key not in FINANCIAL_KEYS
        }
    if isinstance(payload, list):
        return [omit_financial_fields(item) for item in payload]
    return payload
