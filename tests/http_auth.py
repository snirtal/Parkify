"""Sign a test client in against the rolled-back database session."""

from __future__ import annotations

from sqlalchemy.orm import Session

from config.settings import get_settings
from repositories.seed import seed_database
from services.factory import build_services
from services.passwords import Argon2PasswordHasher
from services.unit_of_work import SqlAlchemyUnitOfWork
from services.users import UserService
from services.support import default_id

PASSWORD = "correct-horse-battery"
_FAST_HASHER = Argon2PasswordHasher(time_cost=1, memory_kib=8192, parallelism=1)


class AuthorizedClient:
    """Flask test client that sends the CSRF cookie on changes."""

    def __init__(self, client) -> None:
        self._client = client

    def get(self, *args, **kwargs):
        return self._client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._send("post", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._send("patch", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._send("delete", *args, **kwargs)

    def _send(self, method: str, *args, **kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        cookie = self._client.get_cookie("parkify_csrf")
        if cookie is not None:
            headers.setdefault("X-CSRF-Token", cookie.value)
        return getattr(self._client, method)(*args, headers=headers, **kwargs)


def operator_client(db_session: Session, *, role: str, email: str) -> AuthorizedClient:
    """Seed the facility, create one operator, and sign that operator in."""
    from app import create_app

    get_settings.cache_clear()
    application = create_app("development")
    application.config.update(TESTING=True)
    seed_database(db_session)

    def services():
        return build_services(
            lambda: SqlAlchemyUnitOfWork(db_session, close_session=False, lock_timeout_ms=3000),
            passwords=_FAST_HASHER,
            password_min_length=12,
        )

    application.extensions["service_factory"] = services
    UserService(
        lambda: SqlAlchemyUnitOfWork(db_session, close_session=False, lock_timeout_ms=3000),
        default_id,
        _FAST_HASHER,
        password_min_length=12,
    ).create_user(email=email, full_name="Test Operator", password=PASSWORD, role=role)
    client = application.test_client()
    signed_in = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    if signed_in.status_code != 200:
        raise RuntimeError(f"test sign-in failed with status {signed_in.status_code}")
    return AuthorizedClient(client)
