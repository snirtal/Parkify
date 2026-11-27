"""Create operator accounts. There is no public registration.

Roles are stored for later authorization and are not enforced yet.
admin will have full access. employee will view occupancy and approve
reservations, without financial or administrative access.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import datetime

from models.orm import User
from services.exceptions import ConflictError, ValidationError
from services.passwords import PasswordHasherProtocol
from services.results import UserAccount
from services.support import IdFactory, run_in_transaction

logger = logging.getLogger("parkify.service.users")

ADMIN_ROLE = "admin"
EMPLOYEE_ROLE = "employee"
USER_ROLES = frozenset({ADMIN_ROLE, EMPLOYEE_ROLE})
PASSWORD_MAX_LENGTH = 128
_EMAIL = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")


class UserService:
    """Validate an operator and store only an Argon2id password hash."""

    def __init__(
        self,
        uow_factory: Callable,
        ids: IdFactory,
        passwords: PasswordHasherProtocol,
        *,
        password_min_length: int = 12,
    ) -> None:
        self._uow_factory = uow_factory
        self._ids = ids
        self._passwords = passwords
        self._password_min_length = password_min_length

    def create_user(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
        role: str,
        is_active: bool = True,
    ) -> UserAccount:
        normalized_email = _email(email)
        cleaned_name = _full_name(full_name)
        cleaned_role = _role(role)
        _password(password, self._password_min_length)
        if not isinstance(is_active, bool):
            raise ValidationError("Active status must be true or false.")
        password_hash = self._passwords.hash_password(password)

        def work(uow) -> UserAccount:
            existing = uow.repositories.users.get_by_email(normalized_email)
            if existing is not None:
                raise ConflictError(
                    "A user with this email already exists.",
                    code="email_taken",
                )
            user = User(
                id=self._ids("user"),
                email=normalized_email,
                password_hash=password_hash,
                full_name=cleaned_name,
                role=cleaned_role,
                is_active=is_active,
                created_at=datetime.now().replace(microsecond=0),
            )
            uow.repositories.users.add(user)
            logger.info("created user id=%s role=%s", user.id, user.role)
            return _account(user)

        return run_in_transaction(self._uow_factory, work)


def _account(user: User) -> UserAccount:
    return UserAccount(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _email(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("Enter a valid email address.")
    cleaned = value.strip().lower()
    if len(cleaned) > 254 or _EMAIL.fullmatch(cleaned) is None:
        raise ValidationError("Enter a valid email address.")
    return cleaned


def _full_name(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("Full name must be text.")
    cleaned = value.strip()
    if len(cleaned) < 2:
        raise ValidationError("Full name must be at least 2 characters.")
    if len(cleaned) > 120:
        raise ValidationError("Full name must be 120 characters or fewer.")
    return cleaned


def _role(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("Role must be admin or employee.")
    cleaned = value.strip().lower()
    if cleaned not in USER_ROLES:
        raise ValidationError("Role must be admin or employee.")
    return cleaned


def _password(value: object, minimum: int) -> None:
    if not isinstance(value, str) or value.strip() == "":
        raise ValidationError("Password is required.")
    if len(value) < minimum:
        raise ValidationError(f"Password must be at least {minimum} characters.")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValidationError(f"Password must be {PASSWORD_MAX_LENGTH} characters or fewer.")
