"""Cookie session and CSRF checks.

These helpers are not a global before_request hook. Business routes call
permission_required, which calls require_account. Health and login stay public.
"""

from __future__ import annotations

import secrets

from flask import Response, current_app, request

from controllers.dependencies import current_services
from services.exceptions import AuthenticationError, CsrfError
from services.results import UserAccount

CSRF_HEADER = "X-CSRF-Token"
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def session_cookie_name() -> str:
    return current_app.config["PARKIFY_SETTINGS"].session_cookie


def csrf_cookie_name() -> str:
    return current_app.config["PARKIFY_SETTINGS"].csrf_cookie


def require_account() -> UserAccount:
    """Return the signed-in operator, or raise if the session is missing or dead.

    Cookie-authenticated changes must also present the CSRF token from the
    readable cookie and the signed session.
    """
    token = request.cookies.get(session_cookie_name(), "")
    if not token:
        raise AuthenticationError("Authentication is required.", code="unauthenticated")
    account, csrf_token = current_services().auth.authenticate(token)
    if request.method in _UNSAFE_METHODS:
        _require_csrf(csrf_token)
    return account


def apply_login_cookies(response: Response, *, token: str, csrf_token: str) -> Response:
    settings = current_app.config["PARKIFY_SETTINGS"]
    max_age = settings.jwt_expiration_minutes * 60
    response.set_cookie(
        session_cookie_name(),
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.set_cookie(
        csrf_cookie_name(),
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return response


def clear_auth_cookies(response: Response) -> Response:
    settings = current_app.config["PARKIFY_SETTINGS"]
    for name, httponly in ((session_cookie_name(), True), (csrf_cookie_name(), False)):
        response.delete_cookie(
            name,
            path="/",
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            httponly=httponly,
        )
    return response


def _require_csrf(expected: str) -> None:
    header = request.headers.get(CSRF_HEADER, "")
    cookie = request.cookies.get(csrf_cookie_name(), "")
    if not _same(header, expected) or not _same(cookie, expected):
        raise CsrfError()


def _same(left: str, right: str) -> bool:
    if not left or not right:
        return False
    try:
        return secrets.compare_digest(left, right)
    except (TypeError, ValueError):
        return False
