"""Argon2id password hashing.

Hashes and mismatches are never written to the log.
"""

from __future__ import annotations

import logging
from typing import Protocol

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from config.settings import Settings
from services.exceptions import ValidationError

logger = logging.getLogger("parkify.service.passwords")


class PasswordHasherProtocol(Protocol):
    def hash_password(self, password: str) -> str: ...

    def verify_password(self, password_hash: str, password: str) -> bool: ...


class Argon2PasswordHasher:
    """Hash passwords with Argon2id using the configured cost parameters."""

    def __init__(self, *, time_cost: int, memory_kib: int, parallelism: int) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_kib,
            parallelism=parallelism,
            type=Type.ID,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> Argon2PasswordHasher:
        return cls(
            time_cost=settings.argon2_time_cost,
            memory_kib=settings.argon2_memory_kib,
            parallelism=settings.argon2_parallelism,
        )

    def hash_password(self, password: str) -> str:
        try:
            return self._hasher.hash(password)
        except Exception as exc:
            logger.error("password hashing failed (%s)", type(exc).__name__)
            raise ValidationError("The password could not be stored.") from exc

    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        except Exception as exc:
            logger.error("password verification failed (%s)", type(exc).__name__)
            return False
        return True
