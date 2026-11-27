"""Role permissions. Unknown roles and unknown permissions are denied.

The signed-in role comes from the user row. Callers never accept a role
from the request body.
"""

from __future__ import annotations

OCCUPANCY_READ = "occupancy.read"
SESSIONS_READ = "sessions.read"
GATE_READ = "gate.read"
GATE_OPERATE = "gate.operate"
RESERVATIONS_READ = "reservations.read"
RESERVATIONS_MANAGE = "reservations.manage"
RESERVATIONS_REQUESTS_READ = "reservations.requests.read"
RESERVATIONS_REQUESTS_CREATE = "reservations.requests.create"
RESERVATIONS_APPROVE = "reservations.approve"
RESERVATIONS_REJECT = "reservations.reject"
SETTINGS_READ = "settings.read"
SETTINGS_MANAGE = "settings.manage"
PRICING_READ = "pricing.read"
PRICING_QUOTE = "pricing.quote"

ALL_PERMISSIONS = frozenset(
    {
        OCCUPANCY_READ,
        SESSIONS_READ,
        GATE_READ,
        GATE_OPERATE,
        RESERVATIONS_READ,
        RESERVATIONS_MANAGE,
        RESERVATIONS_REQUESTS_READ,
        RESERVATIONS_REQUESTS_CREATE,
        RESERVATIONS_APPROVE,
        RESERVATIONS_REJECT,
        SETTINGS_READ,
        SETTINGS_MANAGE,
        PRICING_READ,
        PRICING_QUOTE,
    }
)

_EMPLOYEE = frozenset(
    {
        OCCUPANCY_READ,
        RESERVATIONS_REQUESTS_READ,
        RESERVATIONS_APPROVE,
        RESERVATIONS_REJECT,
    }
)
_SIMULATOR = frozenset(
    {
        OCCUPANCY_READ,
        SESSIONS_READ,
        GATE_OPERATE,
        RESERVATIONS_READ,
        RESERVATIONS_REQUESTS_CREATE,
    }
)

ROLE_PERMISSIONS = {
    "admin": ALL_PERMISSIONS,
    "employee": _EMPLOYEE,
    "simulator": _SIMULATOR,
}


def permissions_for(role: str) -> frozenset[str]:
    """Return the permissions stored for this role. An unknown role gets none."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def allows(role: str, permission: str) -> bool:
    """Return whether this role may perform the permission."""
    if permission not in ALL_PERMISSIONS:
        return False
    return permission in permissions_for(role)
