"""Alembic migration environment.

Connection strings are loaded from the repository .env file, then from the
process environment. MIGRATION_DATABASE_URL is preferred, then DATABASE_URL.
Neon direct (non-pooled) URLs are preferred for DDL.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from config.config_loader import load_project_env
from config.database import normalize_database_url
from models.base import Base
import models.orm  # noqa: F401  (registers tables on Base.metadata)

load_project_env()

config = context.config

if config.config_file_name is not None:
    # Leave loggers that the application already configured enabled.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def database_url(*, required: bool) -> str:
    """Resolve the migration URL without printing credentials."""
    raw = (
        os.getenv("MIGRATION_DATABASE_URL")
        or os.getenv("ALEMBIC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or ""
    ).strip()
    if not raw:
        if required:
            raise RuntimeError(
                "Set MIGRATION_DATABASE_URL or DATABASE_URL to a Neon "
                "connection string before running migrations. Use the direct "
                "(non-pooled) hostname for DDL."
            )
        return ""
    return normalize_database_url(raw)


def run_migrations_offline() -> None:
    url = database_url(required=False) or "postgresql+psycopg://unused"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = database_url(required=True)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
