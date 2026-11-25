"""Database configuration tests that do not open a connection."""

from __future__ import annotations

from config.database import normalize_database_url
from config.settings import get_settings


def test_empty_database_url_stays_empty() -> None:
    assert normalize_database_url("  ") == ""


def test_neon_url_uses_psycopg_and_requires_ssl() -> None:
    normalized = normalize_database_url(
        "postgresql://user:secret@ep-example.aws.neon.tech/parkify"
    )
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized
    assert "secret" in normalized


def test_existing_sslmode_is_preserved() -> None:
    normalized = normalize_database_url(
        "postgres://user:secret@host/db?sslmode=verify-full"
    )
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=verify-full" in normalized
    assert "sslmode=require" not in normalized


def test_settings_read_database_url_from_the_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@ep-example.aws.neon.tech/parkify",
    )
    get_settings.cache_clear()
    settings = get_settings("development")
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in settings.database_url
    get_settings.cache_clear()


def test_application_starts_without_a_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    from app import create_app

    application = create_app("development")
    assert application.extensions["db_engine"] is None
    assert application.extensions["db_session_factory"] is None
    get_settings.cache_clear()
