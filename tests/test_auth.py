"""Login, session cookies, CSRF, and logout. Database tests roll back."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from flask import make_response

from config.settings import get_settings
from controllers.authentication import CSRF_HEADER, apply_login_cookies
from services.auth import LoginRateLimiter
from services.factory import build_services
from services.passwords import Argon2PasswordHasher
from services.support import default_id
from services.unit_of_work import SqlAlchemyUnitOfWork
from services.users import UserService

PASSWORD = "correct-horse-battery"


@pytest.fixture()
def auth_client(db_session):
    from app import create_app

    get_settings.cache_clear()
    application = create_app("development")
    application.config.update(TESTING=True)
    application.extensions["login_rate_limiter"] = LoginRateLimiter(
        max_attempts=3,
        window_seconds=900,
    )

    def services():
        return build_services(
            lambda: SqlAlchemyUnitOfWork(db_session, close_session=False),
            rate_limiter=application.extensions["login_rate_limiter"],
        )

    application.extensions["service_factory"] = services
    return application.test_client()


def _create_user(db_session, *, email: str, role: str = "employee", is_active: bool = True):
    settings = get_settings()
    service = UserService(
        lambda: SqlAlchemyUnitOfWork(db_session, close_session=False),
        default_id,
        Argon2PasswordHasher.from_settings(settings),
        password_min_length=settings.password_min_length,
    )
    return service.create_user(
        email=email,
        full_name="Ada Admin",
        password=PASSWORD,
        role=role,
        is_active=is_active,
    )


def _login(client, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _cookie(response, name: str) -> str:
    prefix = f"{name}="
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith(prefix):
            return header.split(";", 1)[0].split("=", 1)[1]
    return ""


def _cookie_header(response, name: str) -> str:
    prefix = f"{name}="
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith(prefix):
            return header
    return ""


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthenticated"


def test_invalid_and_expired_tokens_are_rejected(client):
    settings = get_settings()
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired = jwt.encode(
        {
            "sub": "user-x",
            "jti": "session-x",
            "csrf": "csrf-x",
            "iat": expired_at,
            "exp": expired_at,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    client.set_cookie("parkify_session", expired)
    expired_response = client.get("/api/auth/me")
    assert expired_response.status_code == 401
    assert expired_response.get_json()["error"]["code"] == "token_expired"
    assert expired not in expired_response.get_data(as_text=True)

    client.set_cookie("parkify_session", expired + "tampered")
    invalid = client.get("/api/auth/me")
    assert invalid.status_code == 401
    assert invalid.get_json()["error"]["code"] == "invalid_token"


def test_login_sets_an_httponly_cookie_and_returns_the_role(auth_client, db_session):
    _create_user(db_session, email="ada@example.com", role="admin")
    response = _login(auth_client, "Ada@Example.com", PASSWORD)

    assert response.status_code == 200
    body = response.get_json()["user"]
    assert body["email"] == "ada@example.com"
    assert body["role"] == "admin"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body
    token = _cookie(response, "parkify_session")
    assert token
    assert token not in response.get_data(as_text=True)
    assert PASSWORD not in response.get_data(as_text=True)
    session_cookie = _cookie_header(response, "parkify_session")
    csrf_cookie = _cookie_header(response, "parkify_csrf")
    assert "HttpOnly" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=Lax" in session_cookie
    assert "Secure" not in session_cookie

    me = auth_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["id"] == body["id"]
    assert token not in me.get_data(as_text=True)


def test_unknown_email_and_wrong_password_share_one_error(auth_client, db_session, caplog):
    caplog.set_level(logging.DEBUG)
    _create_user(db_session, email="ada@example.com")
    unknown = _login(auth_client, "missing@example.com", PASSWORD)
    wrong = _login(auth_client, "ada@example.com", PASSWORD + "-no")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.get_json() == wrong.get_json()
    assert unknown.get_json()["error"]["code"] == "invalid_credentials"
    logged = caplog.text
    assert PASSWORD not in logged
    assert "$argon2id$" not in logged


def test_inactive_user_is_rejected_only_after_the_password_matches(auth_client, db_session):
    _create_user(db_session, email="ada@example.com", is_active=False)
    wrong = _login(auth_client, "ada@example.com", PASSWORD + "-no")
    inactive = _login(auth_client, "ada@example.com", PASSWORD)

    assert wrong.status_code == 401
    assert wrong.get_json()["error"]["code"] == "invalid_credentials"
    assert inactive.status_code == 403
    assert inactive.get_json()["error"]["code"] == "account_inactive"
    assert "parkify_session" not in inactive.headers.get("Set-Cookie", "")


def test_logout_requires_csrf_and_invalidates_the_token(auth_client, db_session):
    _create_user(db_session, email="ada@example.com")
    logged_in = _login(auth_client, "ada@example.com", PASSWORD)
    token = _cookie(logged_in, "parkify_session")
    csrf = _cookie(logged_in, "parkify_csrf")

    blocked = auth_client.post("/api/auth/logout")
    assert blocked.status_code == 403
    assert blocked.get_json()["error"]["code"] == "csrf_failed"
    assert auth_client.get("/api/auth/me").status_code == 200

    logged_out = auth_client.post("/api/auth/logout", headers={CSRF_HEADER: csrf})
    assert logged_out.status_code == 204
    auth_client.set_cookie("parkify_session", token)
    auth_client.set_cookie("parkify_csrf", csrf)
    rejected = auth_client.get("/api/auth/me")
    assert rejected.status_code == 401
    assert rejected.get_json()["error"]["code"] == "invalid_token"
    assert token not in rejected.get_data(as_text=True)


def test_login_rate_limit_uses_a_generic_response(auth_client):
    for _ in range(3):
        failed = _login(auth_client, "missing@example.com", PASSWORD)
        assert failed.status_code == 401
    blocked = _login(auth_client, "missing@example.com", PASSWORD)
    assert blocked.status_code == 429
    assert blocked.get_json()["error"]["code"] == "rate_limited"
    assert PASSWORD not in blocked.get_data(as_text=True)


def test_production_cookies_are_secure(client):
    settings = get_settings()
    client.application.config["PARKIFY_SETTINGS"] = replace(
        settings,
        cookie_secure=True,
        cookie_samesite="Strict",
    )
    with client.application.app_context():
        response = make_response("")
        apply_login_cookies(response, token="not-a-real-token", csrf_token="not-a-real-csrf")
    header = _cookie_header(response, "parkify_session")
    assert "Secure" in header
    assert "HttpOnly" in header
    assert "SameSite=Strict" in header
