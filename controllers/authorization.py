"""Require a signed-in operator and an explicit permission.

Every business view uses this decorator. A view without it is unreachable
to anonymous callers only when the route inventory test fails the build.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps

from flask import g

from controllers.authentication import require_account
from services.exceptions import AuthorizationError
from services.permissions import allows
from services.results import UserAccount

logger = logging.getLogger("parkify.authz")


def public_endpoint(view: Callable) -> Callable:
    """Mark a route that stays available without a session."""
    view.public_endpoint = True  # type: ignore[attr-defined]
    return view


def permission_required(*permissions: str) -> Callable:
    """Authenticate, then allow the view only when every permission is granted."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args, **kwargs):
            account = require_account()
            g.parkify_account = account
            missing = [permission for permission in permissions if not allows(account.role, permission)]
            if missing:
                logger.info(
                    "authorization denied role=%s permission=%s",
                    account.role,
                    missing[0],
                )
                raise AuthorizationError()
            return view(*args, **kwargs)

        wrapper.required_permissions = permissions  # type: ignore[attr-defined]
        return wrapper

    return decorator


def current_account() -> UserAccount:
    """Return the operator already loaded for this request."""
    account = getattr(g, "parkify_account", None)
    if account is None:
        account = require_account()
        g.parkify_account = account
    return account
