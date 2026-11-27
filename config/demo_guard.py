"""Refuse to treat an external database as the local Docker demo."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit

DEMO_HOST = "postgres"
DEMO_DATABASE = "parkify"
DEMO_USER = "parkify"
STANDARD_SESSION_COOKIE = "parkify_session"
STANDARD_CSRF_COOKIE = "parkify_csrf"


def assert_demo_database(url: str) -> None:
    """Allow only the Compose Postgres service. Neon and other hosts are refused."""
    if not isinstance(url, str) or not url.strip():
        raise SystemExit("Demo init refuses to run: DATABASE_URL is not set.")
    if "neon.tech" in url.lower():
        raise SystemExit("Demo init refuses to run: this database is not the local demo.")
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    name = parts.path.strip("/")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if (
        host != DEMO_HOST
        or name != DEMO_DATABASE
        or (parts.username or "") != DEMO_USER
        or query.get("sslmode") != "disable"
    ):
        raise SystemExit("Demo init refuses to run: this database is not the local demo.")


_COOKIE_NAME = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def assert_demo_cookie_names(session_name: str, csrf_name: str) -> None:
    """Keep demo sessions from replacing cookies used by the other Parkify apps."""
    if not _COOKIE_NAME.fullmatch(session_name) or not _COOKIE_NAME.fullmatch(csrf_name):
        raise ValueError("Demo cookie names must contain only letters, digits, and underscores.")
    if session_name == STANDARD_SESSION_COOKIE or csrf_name == STANDARD_CSRF_COOKIE:
        raise ValueError("Demo cookie names must be distinct from the standard Parkify cookies.")
    if session_name == csrf_name:
        raise ValueError("Demo session and CSRF cookies must use different names.")
