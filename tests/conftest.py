"""Shared pytest fixtures for the Parkify backend."""

from __future__ import annotations

import pytest

from app import create_app
from config.settings import get_settings


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
