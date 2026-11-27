"""Shared pytest fixtures for the Parkify backend."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app import create_app
from config.config_loader import load_project_env
from config.settings import get_settings
from tests.db_safety import isolated_test_url

load_project_env()


@pytest.fixture()
def app():
    """Create a Flask application configured for testing."""
    get_settings.cache_clear()
    application = create_app("development")
    application.config.update(TESTING=True)
    yield application
    get_settings.cache_clear()


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()


@pytest.fixture(scope="session")
def migrated_engine():
    """Apply migrations to the isolated test branch. Never drops data."""
    url = isolated_test_url()
    previous = os.environ.get("MIGRATION_DATABASE_URL")
    os.environ["MIGRATION_DATABASE_URL"] = url
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if previous is None:
            os.environ.pop("MIGRATION_DATABASE_URL", None)
        else:
            os.environ["MIGRATION_DATABASE_URL"] = previous
    engine = create_engine(url, poolclass=NullPool)
    yield engine
    engine.dispose()


def _hide_committed_activity(session: Session) -> None:
    """Hide activity already stored on the test branch for this transaction only.

    The simulator commits vehicles, sessions, and gate events on the same
    branch. Seed merges the catalog rows but does not remove those extras, so
    snapshot counts and open spots would depend on earlier simulator runs.
    These deletes stay inside the connection transaction started above and are
    rolled back with it. Nothing is committed.
    """
    session.execute(text("DELETE FROM auth_sessions"))
    session.execute(text("DELETE FROM gate_activities"))
    session.execute(text("DELETE FROM parking_sessions"))
    session.execute(text("DELETE FROM reservations"))
    session.execute(text("DELETE FROM vehicles"))
    session.flush()


@pytest.fixture()
def db_session(migrated_engine):
    """A transaction that is always rolled back, including seed commits."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        _hide_committed_activity(session)
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
