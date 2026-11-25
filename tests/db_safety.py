"""Guards that keep integration tests off the primary Neon database."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import pytest

from config.database import normalize_database_url

_PLACEHOLDERS = ("USER:PASSWORD", "ep-example")


def database_identity(url: str) -> tuple[str, str]:
    """Return the Neon endpoint and database name, ignoring the pooler suffix."""
    parts = urlsplit(normalize_database_url(url))
    hostname = (parts.hostname or "").lower()
    if hostname.endswith(".neon.tech"):
        labels = hostname.split(".")
        labels[0] = labels[0].removesuffix("-pooler")
        hostname = ".".join(labels)
    database_name = parts.path.rstrip("/") or "/"
    return hostname, database_name


def isolated_test_url() -> str:
    """Return TEST_DATABASE_URL, or skip when it is missing or not isolated."""
    raw = os.getenv("TEST_DATABASE_URL", "").strip()
    if not raw or any(marker in raw for marker in _PLACEHOLDERS):
        pytest.skip(
            "SKIPPED: TEST_DATABASE_URL is not configured. Create an isolated "
            "Neon branch and set TEST_DATABASE_URL before running database "
            "integration tests."
        )
    test_identity = database_identity(raw)
    protected = [
        os.getenv("DATABASE_URL", ""),
        os.getenv("MIGRATION_DATABASE_URL", ""),
    ]
    for candidate in protected:
        if candidate.strip() and database_identity(candidate) == test_identity:
            pytest.skip(
                "SKIPPED: TEST_DATABASE_URL points at the primary database. "
                "Use a separate Neon branch so tests cannot change primary data."
            )
    return normalize_database_url(raw)
