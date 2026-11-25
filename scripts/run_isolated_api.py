"""Run Flask against the isolated Neon branch on 127.0.0.1:5002.

The process refuses to start when TEST_DATABASE_URL is missing or points at
the primary database. It does not print connection strings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values

from tests.db_safety import database_identity


def isolated_database_url() -> str:
    """Return the test URL after proving it is not the primary database."""
    values = dotenv_values(ROOT / ".env")
    test = (values.get("TEST_DATABASE_URL") or "").strip()
    primary = (values.get("DATABASE_URL") or "").strip()
    migration = (values.get("MIGRATION_DATABASE_URL") or "").strip()
    if not test:
        raise SystemExit("TEST_DATABASE_URL is not configured.")
    test_identity = database_identity(test)
    if primary and database_identity(primary) == test_identity:
        raise SystemExit("Refusing to start: the test database is the primary database.")
    if migration and database_identity(migration) == test_identity:
        raise SystemExit("Refusing to start: the test database is the migration database.")
    return test


def main() -> None:
    os.environ["DATABASE_URL"] = isolated_database_url()
    os.environ["HOST"] = "127.0.0.1"
    os.environ["PORT"] = "5002"
    os.environ["DEBUG"] = "false"
    os.environ["PARKIFY_ENV"] = "development"
    os.environ["CORS_ORIGINS"] = "http://127.0.0.1:5174,http://localhost:5174"

    from config.settings import get_settings

    get_settings.cache_clear()
    import app as app_module

    settings = app_module.app.config["PARKIFY_SETTINGS"]
    if database_identity(settings.database_url) != database_identity(os.environ["DATABASE_URL"]):
        raise SystemExit("Refusing to start: the app resolved a different database.")
    if settings.port != 5002:
        raise SystemExit("Refusing to start: unexpected port.")
    print("Parkify isolated API http://127.0.0.1:5002", flush=True)
    app_module.app.run(host="127.0.0.1", port=5002, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
