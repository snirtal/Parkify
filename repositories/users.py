"""Operator account repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.orm import User
from repositories.base import SqlAlchemyCrudRepository, _guarded


class UserRepository(Protocol):
    def get(self, entity_id: str) -> User | None: ...

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[User]: ...

    def add(self, entity: User) -> User: ...

    def delete(self, entity: User) -> None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def get_for_update(self, entity_id: str) -> User | None: ...


class SqlAlchemyUserRepository(SqlAlchemyCrudRepository[User]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    @_guarded("get_by_email")
    def get_by_email(self, email: str) -> User | None:
        self.logger.debug("get_by_email")
        statement = select(User).where(User.email == email)
        return self.session.scalar(statement)
