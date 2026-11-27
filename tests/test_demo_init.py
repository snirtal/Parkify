"""Guards for the local Docker demo initializer. These tests use no database."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "docker" / "demo" / "init_demo.py"
_SPEC = importlib.util.spec_from_file_location("init_demo", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
init_demo = importlib.util.module_from_spec(_SPEC)
sys.modules["init_demo"] = init_demo
_SPEC.loader.exec_module(init_demo)

LOCAL = "postgresql://parkify:parkify@postgres:5432/parkify?sslmode=disable"


def test_demo_init_accepts_only_the_local_compose_database():
    init_demo.assert_demo_database(LOCAL)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "postgresql://parkify:parkify@ep-example.neon.tech/parkify?sslmode=require",
        "postgresql://parkify:parkify@postgres:5432/parkify?sslmode=require",
        "postgresql://parkify:parkify@postgres:5432/other?sslmode=disable",
        "postgresql://other:parkify@postgres:5432/parkify?sslmode=disable",
        "postgresql://parkify:secret@db.example/parkify?sslmode=disable",
    ],
)
def test_demo_init_refuses_remote_and_production_databases(url):
    with pytest.raises(SystemExit, match="not the local demo|DATABASE_URL is not set"):
        init_demo.assert_demo_database(url)


def test_seed_runs_only_when_the_facility_is_missing():
    assert init_demo.should_seed(False) is True
    assert init_demo.should_seed(True) is False


def test_demo_users_are_created_once_and_existing_passwords_stay():
    created_emails: list[str] = []

    def create(account) -> None:
        created_emails.append(account.email)

    first_created, first_present = init_demo.ensure_demo_users(lambda _email: None, create)
    assert first_created == 3
    assert first_present == 0
    assert created_emails == [account.email for account in init_demo.DEMO_ACCOUNTS]

    again_created, again_present = init_demo.ensure_demo_users(lambda _email: object(), create)
    assert again_created == 0
    assert again_present == 3
    assert len(created_emails) == 3


def test_demo_settings_allow_local_http_and_refuse_a_remote_database(monkeypatch):
    from config.settings import get_settings

    monkeypatch.setenv("PARKIFY_ENV", "demo")
    monkeypatch.setenv("DATABASE_URL", LOCAL)
    monkeypatch.setenv("JWT_SECRET", "parkify-demo-jwt-secret-not-for-production")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("SESSION_COOKIE_NAME", "parkify_demo_session")
    monkeypatch.setenv("CSRF_COOKIE_NAME", "parkify_demo_csrf")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.environment == "demo"
        assert settings.cookie_secure is False
        assert settings.session_cookie == "parkify_demo_session"
        assert settings.csrf_cookie == "parkify_demo_csrf"
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://parkify:parkify@ep-example.neon.tech/parkify?sslmode=require",
        )
        get_settings.cache_clear()
        with pytest.raises(SystemExit, match="not the local demo"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_production_still_requires_secure_cookies(monkeypatch):
    from config.settings import get_settings

    monkeypatch.setenv("PARKIFY_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://parkify:parkify@db.example/parkify?sslmode=require")
    monkeypatch.setenv("JWT_SECRET", "parkify-demo-jwt-secret-not-for-production")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="Secure"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_documented_demo_passwords_meet_the_policy():
    assert len(init_demo.DEMO_ACCOUNTS) == 3
    assert {account.role for account in init_demo.DEMO_ACCOUNTS} == {"admin", "employee", "simulator"}
    for account in init_demo.DEMO_ACCOUNTS:
        assert len(account.password) >= 12
        assert account.email.endswith("@parkify.demo")
