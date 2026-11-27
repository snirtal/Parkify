"""Identity of the seeded Skyline facility.

The seed snapshot always uses DEFAULT_FACILITY_ID. The frontend and live
simulator use the same id unless FACILITY_ID overrides it.
"""

from __future__ import annotations

import os

DEFAULT_FACILITY_ID = "facility-skyline"


def configured_facility_id() -> str:
    """Return FACILITY_ID when it is set, otherwise the seeded facility."""
    configured = os.getenv("FACILITY_ID", "").strip()
    return configured or DEFAULT_FACILITY_ID
