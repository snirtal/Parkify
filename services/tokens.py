"""Signed, expiring login tokens.

The encoded token is a credential. It is never logged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from services.exceptions import AuthenticationError

_ALGORITHM = "HS256"
_REQUIRED = ["exp", "sub", "jti", "csrf"]


@dataclass(frozen=True)
class TokenClaims:
    user_id: str
    session_id: str
    csrf_token: str
    expires_at: datetime

    def __repr__(self) -> str:
        return f"TokenClaims(user_id={self.user_id!r}, session_id={self.session_id!r})"


class TokenService:
    """Issue and read HS256 JWTs."""

    def __init__(self, *, secret: str, expiration_minutes: int) -> None:
        self._secret = secret
        self._expiration = timedelta(minutes=expiration_minutes)

    def expiration(self, now: datetime) -> datetime:
        return now + self._expiration

    def issue(self, *, user_id: str, session_id: str, csrf_token: str, now: datetime) -> str:
        expires_at = self.expiration(now)
        payload = {
            "sub": user_id,
            "jti": session_id,
            "csrf": csrf_token,
            "iat": _timestamp(now),
            "exp": _timestamp(expires_at),
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def read(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[_ALGORITHM],
                options={"require": _REQUIRED},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("The session has expired.", code="token_expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("The session is not valid.", code="invalid_token") from exc
        expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc).replace(tzinfo=None)
        return TokenClaims(
            user_id=str(payload["sub"]),
            session_id=str(payload["jti"]),
            csrf_token=str(payload["csrf"]),
            expires_at=expires_at,
        )


def _timestamp(moment: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.timestamp())
