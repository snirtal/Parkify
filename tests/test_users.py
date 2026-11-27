"""Operator accounts. Database tests use the isolated branch and roll back."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import inspect, select

from config.settings import _bounded_int, get_settings
from models.orm import User
from scripts.create_user import build_parser, execute, read_password, success_message
from services.exceptions import ConflictError, ValidationError
from services.passwords import Argon2PasswordHasher
from services.results import UserAccount
from services.support import default_id
from services.unit_of_work import SqlAlchemyUnitOfWork
from services.users import UserService

PASSWORD = "correct-horse-battery"


class _Users:
    def __init__(self) -> None:
        self.by_email: dict[str, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return self.by_email.get(email)

    def add(self, user: User) -> User:
        self.by_email[user.email] = user
        return user


class _UnitOfWork:
    def __init__(self, users: _Users) -> None:
        self.repositories = SimpleNamespace(users=users)

    def __enter__(self) -> _UnitOfWork:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


class _Hasher:
    def hash_password(self, password: str) -> str:
        return f"hash:{len(password)}"

    def verify_password(self, password_hash: str, password: str) -> bool:
        return password_hash == f"hash:{len(password)}"


def _service(users: _Users | None = None) -> tuple[UserService, _Users]:
    store = users or _Users()
    service = UserService(
        lambda: _UnitOfWork(store),
        lambda prefix: f"{prefix}-fixed",
        _Hasher(),
        password_min_length=12,
    )
    return service, store


def test_argon2id_hash_verifies_without_storing_the_password() -> None:
    hasher = Argon2PasswordHasher(time_cost=2, memory_kib=8192, parallelism=1)
    password_hash = hasher.hash_password(PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert PASSWORD not in password_hash
    assert hasher.verify_password(password_hash, PASSWORD) is True
    assert hasher.verify_password(password_hash, PASSWORD + "x") is False
    assert hasher.hash_password(PASSWORD) != password_hash


def test_create_user_normalizes_email_and_hides_secrets_from_logs(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    service, store = _service()
    account = service.create_user(
        email=" Ada@Example.com ",
        full_name=" Ada Admin ",
        password=PASSWORD,
        role="Admin",
    )

    assert account.email == "ada@example.com"
    assert account.role == "admin"
    assert account.id == "user-fixed"
    assert "password_hash" not in account.__dataclass_fields__
    stored = store.by_email["ada@example.com"]
    assert stored.password_hash == f"hash:{len(PASSWORD)}"
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert PASSWORD not in messages
    assert stored.password_hash not in messages
    assert "created user id=user-fixed role=admin" in messages


def test_duplicate_email_is_rejected_without_the_address() -> None:
    service, _store = _service()
    service.create_user(
        email="ada@example.com",
        full_name="Ada Admin",
        password=PASSWORD,
        role="employee",
    )
    with pytest.raises(ConflictError, match="already exists") as caught:
        service.create_user(
            email="ADA@example.com",
            full_name="Ada Admin",
            password=PASSWORD,
            role="employee",
        )
    assert caught.value.code == "email_taken"
    assert "ada@example.com" not in caught.value.message
    assert PASSWORD not in caught.value.message


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"email": "not-an-email", "full_name": "Ada Admin", "password": PASSWORD, "role": "admin"}, "email"),
        ({"email": "ada@example.com", "full_name": "A", "password": PASSWORD, "role": "admin"}, "Full name"),
        ({"email": "ada@example.com", "full_name": "Ada Admin", "password": "short-pass", "role": "admin"}, "Password"),
        ({"email": "ada@example.com", "full_name": "Ada Admin", "password": PASSWORD, "role": "guest"}, "Role"),
    ],
)
def test_invalid_accounts_are_rejected(kwargs, message) -> None:
    service, _store = _service()
    with pytest.raises(ValidationError, match=message):
        service.create_user(**kwargs)


def test_user_repr_omits_the_password_hash() -> None:
    user = User(
        id="user-1",
        email="ada@example.com",
        password_hash="$argon2id$secret-hash",
        full_name="Ada Admin",
        role="admin",
        is_active=True,
        created_at=datetime(2026, 11, 27, 16, 0),
    )
    rendered = repr(user)
    assert "secret-hash" not in rendered
    assert "ada@example.com" not in rendered


def test_password_length_configuration_rejects_unsafe_bounds() -> None:
    with pytest.raises(ValueError, match="password_min_length"):
        _bounded_int(4, "password_min_length", minimum=8, maximum=128)


def test_cli_has_no_password_argument_and_prompts_without_echo() -> None:
    assert all(action.dest != "password" for action in build_parser()._actions)
    prompts: list[str] = []

    def reader(prompt: str) -> str:
        prompts.append(prompt)
        return PASSWORD

    assert read_password(reader) == PASSWORD
    assert prompts == ["Password: ", "Confirm password: "]


def _mismatch(prompt: str) -> str:
    return {"Password: ": "one-password-1", "Confirm password: ": "other-password"}[prompt]


def test_cli_rejects_a_mismatched_confirmation() -> None:
    with pytest.raises(SystemExit, match="do not match"):
        read_password(_mismatch)


def test_cli_execution_does_not_print_the_password(capsys) -> None:
    captured_password: dict[str, str] = {}

    class _Service:
        def create_user(self, **kwargs):
            captured_password["password"] = kwargs["password"]
            return UserAccount(
                id="user-1",
                email=kwargs["email"],
                full_name=kwargs["full_name"],
                role=kwargs["role"],
                is_active=True,
                created_at=datetime(2026, 11, 27, 16, 0),
            )

    account = execute(
        argparse.Namespace(email="Ada@Example.com", full_name="Ada Admin", role="admin"),
        lambda _prompt: PASSWORD,
        _Service(),
    )
    output = capsys.readouterr()
    assert captured_password["password"] == PASSWORD
    assert PASSWORD not in output.out
    assert PASSWORD not in output.err
    assert PASSWORD not in success_message(account)
    assert success_message(account) == "Created user user-1 role=admin"


def test_users_migration_is_applied_on_the_isolated_database(migrated_engine) -> None:
    columns = {column["name"] for column in inspect(migrated_engine).get_columns("users")}
    assert columns == {
        "id",
        "email",
        "password_hash",
        "full_name",
        "role",
        "is_active",
        "created_at",
    }


def test_create_user_persists_an_argon2id_hash_and_rolls_back(db_session) -> None:
    settings = get_settings()
    hasher = Argon2PasswordHasher.from_settings(settings)
    service = UserService(
        lambda: SqlAlchemyUnitOfWork(db_session, close_session=False),
        default_id,
        hasher,
        password_min_length=settings.password_min_length,
    )
    account = service.create_user(
        email="Ada@Example.com",
        full_name="Ada Admin",
        password=PASSWORD,
        role="employee",
        is_active=True,
    )

    stored = db_session.scalar(select(User).where(User.id == account.id))
    assert stored is not None
    assert stored.email == "ada@example.com"
    assert stored.role == "employee"
    assert stored.is_active is True
    assert stored.password_hash.startswith("$argon2id$")
    assert PASSWORD not in stored.password_hash
    assert hasher.verify_password(stored.password_hash, PASSWORD) is True
    with pytest.raises(ConflictError):
        service.create_user(
            email="ada@example.com",
            full_name="Ada Admin",
            password=PASSWORD,
            role="admin",
        )
