"""Sign-in, session lookup, and logout.

Failed passwords and unknown emails share one error. Inactive accounts are
rejected only after the password matches. Tokens are not logged.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from models.orm import AuthSession
from services.exceptions import AuthenticationError, InactiveAccountError, RateLimitError
from services.passwords import PasswordHasherProtocol
from services.results import UserAccount
from services.support import run_in_transaction
from services.tokens import TokenService
from services.users import _account, _email

logger = logging.getLogger("parkify.service.auth")
INVALID_CREDENTIALS = "The email or password is incorrect."


@dataclass(frozen=True)
class LoginResult:
    account: UserAccount
    token: str
    csrf_token: str

    def __repr__(self) -> str:
        return f"LoginResult(user_id={self.account.id!r}, role={self.account.role!r})"


class LoginRateLimiter:
    """Process-local limit for sign-in attempts. The key is never a password."""

    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            if len(recent) >= self._max_attempts:
                raise RateLimitError()

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            recent.append(now)
            self._failures[key] = recent

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def _recent(self, key: str, now: float) -> list[float]:
        """Return failures still inside the window. Caller must hold the lock."""
        recent = [stamp for stamp in self._failures.get(key, []) if now - stamp < self._window_seconds]
        self._failures[key] = recent
        return recent


class AuthService:
    """Authenticate an operator and bind the JWT to a revocable session row."""

    def __init__(
        self,
        uow_factory: Callable,
        passwords: PasswordHasherProtocol,
        tokens: TokenService,
        rate_limiter: LoginRateLimiter,
    ) -> None:
        self._uow_factory = uow_factory
        self._passwords = passwords
        self._tokens = tokens
        self._rate_limiter = rate_limiter

    def login(self, *, email: str, password: str, client_key: str) -> LoginResult:
        normalized = _email(email)
        limit_key = _limit_key(client_key, normalized)
        self._rate_limiter.check(limit_key)
        now = _utc_now()

        def work(uow) -> LoginResult:
            user = uow.repositories.users.get_by_email(normalized)
            if user is None:
                self._passwords.verify_password(_dummy_hash(self._passwords), password)
                raise AuthenticationError(INVALID_CREDENTIALS, code="invalid_credentials")
            if not self._passwords.verify_password(user.password_hash, password):
                raise AuthenticationError(INVALID_CREDENTIALS, code="invalid_credentials")
            if not user.is_active:
                logger.info("login rejected inactive user id=%s", user.id)
                raise InactiveAccountError()
            session_id = secrets.token_urlsafe(32)
            csrf_token = secrets.token_urlsafe(32)
            expires_at = self._tokens.expiration(now)
            uow.repositories.auth_sessions.add(
                AuthSession(
                    id=session_id,
                    user_id=user.id,
                    expires_at=expires_at,
                    created_at=now,
                )
            )
            token = self._tokens.issue(
                user_id=user.id,
                session_id=session_id,
                csrf_token=csrf_token,
                now=now,
            )
            logger.info("login succeeded user id=%s", user.id)
            return LoginResult(account=_account(user), token=token, csrf_token=csrf_token)

        try:
            result = run_in_transaction(self._uow_factory, work)
        except InactiveAccountError:
            self._rate_limiter.record_failure(limit_key)
            raise
        except AuthenticationError:
            self._rate_limiter.record_failure(limit_key)
            logger.info("login failed")
            raise
        self._rate_limiter.clear(limit_key)
        return result

    def authenticate(self, token: str) -> tuple[UserAccount, str]:
        claims = self._tokens.read(token)
        now = _utc_now()

        def work(uow) -> tuple[UserAccount, str]:
            session = uow.repositories.auth_sessions.get(claims.session_id)
            if session is None or session.expires_at <= now or session.user_id != claims.user_id:
                raise AuthenticationError("The session is not valid.", code="invalid_token")
            user = uow.repositories.users.get(claims.user_id)
            if user is None or not user.is_active:
                raise AuthenticationError("The session is not valid.", code="invalid_token")
            return _account(user), claims.csrf_token

        return run_in_transaction(self._uow_factory, work)

    def logout(self, token: str) -> None:
        claims = self._tokens.read(token)

        def work(uow) -> None:
            session = uow.repositories.auth_sessions.get(claims.session_id)
            if session is not None:
                uow.repositories.auth_sessions.delete(session)
            logger.info("logout user id=%s", claims.user_id)

        run_in_transaction(self._uow_factory, work)


def _limit_key(client_key: str, email: str) -> str:
    client = (client_key or "unknown").strip()[:64]
    return f"{client}|{email}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


_dummy_hashes: dict[int, str] = {}


def _dummy_hash(passwords: PasswordHasherProtocol) -> str:
    key = id(passwords)
    cached = _dummy_hashes.get(key)
    if cached is None:
        cached = passwords.hash_password("parkify-dummy-password")
        _dummy_hashes[key] = cached
    return cached
