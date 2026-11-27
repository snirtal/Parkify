"""Every API route is public or explicitly permitted. Unknown roles are denied."""

from __future__ import annotations

from services.permissions import (
    ALL_PERMISSIONS,
    RESERVATIONS_APPROVE,
    allows,
    permissions_for,
)


def test_unknown_roles_and_permissions_are_denied():
    assert permissions_for("admin") == ALL_PERMISSIONS
    assert allows("employee", "occupancy.read")
    assert allows("employee", RESERVATIONS_APPROVE)
    assert not allows("employee", "settings.read")
    assert not allows("employee", "pricing.read")
    assert not allows("employee", "gate.operate")
    assert not allows("contractor", "occupancy.read")
    assert not allows("admin", "not.a.permission")


def test_every_api_route_is_public_or_protected(app):
    unprotected = []
    used = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api"):
            continue
        view = app.view_functions[rule.endpoint]
        if getattr(view, "public_endpoint", False):
            continue
        permissions = getattr(view, "required_permissions", None)
        if permissions is None:
            unprotected.append(f"{sorted(rule.methods)} {rule.rule}")
            continue
        used.update(permissions)
    assert unprotected == []
    assert RESERVATIONS_APPROVE not in used
    assert "occupancy.read" in used
    assert "settings.manage" in used
    assert "pricing.quote" in used
