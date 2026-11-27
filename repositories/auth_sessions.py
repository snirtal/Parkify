"""Login session repository. Rows are deleted on logout."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from models.orm import AuthSession
from repositories.base import SqlAlchemyCrudRepository, _guarded


class AuthSessionRepository(Protocol):
    def get(self, entity_id: str) -> AuthSession | None: ...

    def add(self, entity: AuthSession) -> AuthSession: ...

    def delete(self, entity: AuthSession) -> None: ...


class SqlAlchemyAuthSessionRepository(SqlAlchemyCrudRepository[AuthSession]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, AuthSession)

    @_guarded("get")
    def get(self, entity_id: str) -> AuthSession | None:
        self.logger.debug("get session")
        return self.session.get(self.model, entity_id)
