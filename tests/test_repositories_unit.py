"""Repository tests that do not open a database connection."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from models.orm import FacilitySettings
from repositories.base import SqlAlchemyCrudRepository
from repositories.exceptions import RepositoryError
from repositories.factory import build_repositories
from repositories.facilities import SqlAlchemyFacilitySettingsRepository
from tests.db_safety import database_identity, isolated_test_url


def test_repository_modules_do_not_import_flask() -> None:
    root = Path("repositories")
    modules = [path for path in root.glob("*.py") if path.name != "seed.py"]
    for path in modules:
        tree = ast.parse(path.read_text())
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        assert "flask" not in imported


def test_add_and_delete_do_not_commit() -> None:
    session = MagicMock()
    repository = SqlAlchemyCrudRepository(session, FacilitySettings)
    entity = FacilitySettings(
        id="settings-1",
        facility_id="facility-1",
        hourly_rate=Decimal("4.20"),
        daily_max_rate=Decimal("28.00"),
        grace_period_minutes=15,
        ev_surcharge=Decimal("0.60"),
        high_occupancy_alert=True,
        reservation_overstay_alert=True,
        space_fault_alert=True,
    )
    repository.add(entity)
    repository.delete(entity)
    session.add.assert_called_once_with(entity)
    session.delete.assert_called_once_with(entity)
    session.commit.assert_not_called()
    session.rollback.assert_not_called()


def test_repository_error_does_not_include_the_connection_string(caplog) -> None:
    session = MagicMock()
    session.get.side_effect = SQLAlchemyError("postgresql://user:secret@db.example/parkify")
    repository = SqlAlchemyCrudRepository(session, FacilitySettings)
    with pytest.raises(RepositoryError, match="get failed") as caught:
        repository.get("settings-1")
    assert "secret" not in str(caught.value)
    assert "postgresql://" not in caplog.text


def test_settings_update_assigns_only_supplied_fields() -> None:
    repository = SqlAlchemyFacilitySettingsRepository(MagicMock())
    settings = FacilitySettings(
        id="settings-1",
        facility_id="facility-1",
        hourly_rate=Decimal("4.20"),
        daily_max_rate=Decimal("28.00"),
        grace_period_minutes=15,
        ev_surcharge=Decimal("0.60"),
        high_occupancy_alert=True,
        reservation_overstay_alert=True,
        space_fault_alert=True,
    )
    repository.apply_changes(settings, hourly_rate=Decimal("5.00"), space_fault_alert=False)
    assert settings.hourly_rate == Decimal("5.00")
    assert settings.space_fault_alert is False
    assert settings.daily_max_rate == Decimal("28.00")
    repository.session.commit.assert_not_called()


def test_build_repositories_uses_one_session() -> None:
    session = MagicMock()
    repositories = build_repositories(session)
    assert repositories.spots.session is session
    assert repositories.reservations.session is session
    assert repositories.gate_activities.session is session


def test_invalid_page_is_rejected_without_a_query() -> None:
    session = MagicMock()
    repository = SqlAlchemyCrudRepository(session, FacilitySettings)
    with pytest.raises(RepositoryError, match="limit must be at least 1"):
        repository.list(limit=0)
    session.scalars.assert_not_called()


def test_pooler_and_direct_hosts_identify_the_same_database() -> None:
    pooled = "postgresql://user:secret@ep-example-pooler.region.aws.neon.tech/parkify?sslmode=require"
    direct = "postgresql://user:other@ep-example.region.aws.neon.tech/parkify"
    other_branch = "postgresql://user:secret@ep-branch.region.aws.neon.tech/parkify"
    other_database = "postgresql://user:secret@ep-example.region.aws.neon.tech/parkify_test"
    assert database_identity(pooled) == database_identity(direct)
    assert database_identity(pooled) != database_identity(other_branch)
    assert database_identity(direct) != database_identity(other_database)


def test_isolated_test_url_rejects_the_primary_database(monkeypatch) -> None:
    primary = "postgresql://user:secret@ep-primary-pooler.region.aws.neon.tech/parkify"
    monkeypatch.setenv("DATABASE_URL", primary)
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "")
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql://user:other@ep-primary.region.aws.neon.tech/parkify?sslmode=require",
    )
    with pytest.raises(pytest.skip.Exception):
        isolated_test_url()
