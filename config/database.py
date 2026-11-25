"""SQLAlchemy engine and request-scoped session management.

The database host is provider-agnostic. Neon is the intended host, and the
connection string always comes from the environment.
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from flask import Flask, g
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger("parkify.database")


class DatabaseConnectionError(RuntimeError):
    """Raised when the configured database cannot be reached."""


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when a database session is requested without DATABASE_URL."""


def normalize_database_url(url: str) -> str:
    """Use the psycopg v3 driver and require SSL unless the URL already sets it."""
    cleaned = url.strip()
    if not cleaned:
        return ""

    if cleaned.startswith("postgres://"):
        cleaned = "postgresql://" + cleaned[len("postgres://") :]
    if cleaned.startswith("postgresql://"):
        cleaned = "postgresql+psycopg://" + cleaned[len("postgresql://") :]

    parts = urlsplit(cleaned)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def create_db_engine(database_url: str) -> Engine:
    """Create a pooled engine. The first real connection happens on checkout."""
    engine = create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=30,
        pool_recycle=300,
        future=True,
    )

    @event.listens_for(engine, "handle_error")
    def _log_db_error(context) -> None:  # noqa: ANN001
        error = context.original_exception
        logger.error("Database error (%s)", type(error).__name__)

    return engine


def check_database_connection(engine: Engine) -> None:
    """Open one connection and log success or failure without printing the URL."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Database connection failed (%s)", type(exc).__name__)
        raise DatabaseConnectionError(
            "Unable to connect to the configured PostgreSQL database."
        ) from exc
    logger.info("Database connection established")


def init_database(app: Flask) -> None:
    """Attach a pooled engine when DATABASE_URL is configured.

    Tables are never created here. Alembic owns the schema.
    """
    database_url = app.config["PARKIFY_SETTINGS"].database_url
    if not database_url:
        logger.info("DATABASE_URL is not set; database sessions are disabled")
        app.extensions["db_engine"] = None
        app.extensions["db_session_factory"] = None
    else:
        engine = create_db_engine(database_url)
        factory = sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
        app.extensions["db_engine"] = engine
        app.extensions["db_session_factory"] = factory

    @app.teardown_appcontext
    def _close_session(exception: BaseException | None) -> None:
        session: Session | None = g.pop("db_session", None)
        if session is None:
            return
        if exception is not None:
            session.rollback()
            logger.warning(
                "Rolled back the request database session after %s",
                type(exception).__name__,
            )
        session.close()


def get_db_session() -> Session:
    """Return the session for the current application context."""
    from flask import current_app

    factory = current_app.extensions.get("db_session_factory")
    if factory is None:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL is not configured. Add a Neon connection string to .env."
        )
    session = g.get("db_session")
    if session is None:
        session = factory()
        g.db_session = session
    return session
