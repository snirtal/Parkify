"""Generic repository contract and SQLAlchemy CRUD implementation.

Repositories never commit or roll back. The caller owns the transaction.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from functools import wraps
from typing import Generic, Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from repositories.exceptions import RepositoryError

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """One page of a filtered query."""

    items: list[T]
    total: int
    limit: int
    offset: int


class CrudRepository(Protocol[T]):
    """Operations shared by every entity repository."""

    def get(self, entity_id: str) -> T | None:
        """Return the row with this primary key, or None."""

    def list(self, *, limit: int | None = None, offset: int = 0) -> Sequence[T]:
        """Return rows ordered by primary key."""

    def add(self, entity: T) -> T:
        """Stage an insert or update. Does not commit."""

    def delete(self, entity: T) -> None:
        """Stage a delete. Does not commit."""


def _guarded(operation: str):
    """Log database failures by exception type and raise RepositoryError."""

    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except RepositoryError:
                raise
            except SQLAlchemyError as exc:
                self.logger.error("%s failed (%s)", operation, type(exc).__name__)
                raise RepositoryError(f"{operation} failed") from exc

        return wrapper

    return decorator


class SqlAlchemyCrudRepository(Generic[T]):
    """SQLAlchemy implementation of the shared CRUD operations."""

    def __init__(self, session: Session, model: type[T]) -> None:
        self.session = session
        self.model = model
        table_name = getattr(model, "__tablename__", model.__name__)
        self.logger = logging.getLogger(f"parkify.repository.{table_name}")

    @_guarded("get")
    def get(self, entity_id: str) -> T | None:
        self.logger.debug("get id=%s", entity_id)
        return self.session.get(self.model, entity_id)

    @_guarded("list")
    def list(self, *, limit: int | None = None, offset: int = 0) -> list[T]:
        _validate_page(limit, offset)
        statement = select(self.model).order_by(self.model.id).offset(offset)  # type: ignore[attr-defined]
        if limit is not None:
            statement = statement.limit(limit)
        self.logger.debug("list limit=%s offset=%s", limit, offset)
        return list(self.session.scalars(statement))

    @_guarded("add")
    def add(self, entity: T) -> T:
        self.session.add(entity)
        self.logger.debug("add")
        return entity

    @_guarded("delete")
    def delete(self, entity: T) -> None:
        self.session.delete(entity)
        self.logger.debug("delete")


def _validate_page(limit: int | None, offset: int) -> None:
    if offset < 0:
        raise RepositoryError("offset must be zero or greater")
    if limit is not None and limit < 1:
        raise RepositoryError("limit must be at least 1")
