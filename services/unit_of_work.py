"""Transaction boundary for one business operation.

Repositories only stage changes. A service commits or rolls back through
this unit of work, so a session and its gate event either both persist
or neither does.
"""

from __future__ import annotations

import logging
from types import TracebackType

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from repositories.factory import Repositories, build_repositories
from services.exceptions import ConstraintConflict

logger = logging.getLogger("parkify.service.transaction")


class SqlAlchemyUnitOfWork:
    """One SQLAlchemy session and the repositories bound to it."""

    def __init__(
        self,
        session: Session,
        *,
        close_session: bool = False,
        lock_timeout_ms: int | None = 3000,
    ) -> None:
        if lock_timeout_ms is not None and not 1 <= int(lock_timeout_ms) <= 60_000:
            raise ValueError("lock_timeout_ms must be between 1 and 60000")
        self.session = session
        self.repositories = build_repositories(session)
        self._close_session = close_session
        self._lock_timeout_ms = None if lock_timeout_ms is None else int(lock_timeout_ms)
        self._timeout_applied = False

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._apply_lock_timeout()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            if self._close_session:
                self.session.close()

    def flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as exc:
            self._reject(exc, "The operation conflicts with existing data.")
        except OperationalError as exc:
            self._reject(
                exc,
                "The operation could not be completed because of a concurrent update.",
            )

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self._reject(exc, "The operation conflicts with existing data.")
        except OperationalError as exc:
            self._reject(
                exc,
                "The operation could not be completed because of a concurrent update.",
            )

    def rollback(self) -> None:
        if self.session.in_transaction():
            self.session.rollback()

    def _apply_lock_timeout(self) -> None:
        if self._lock_timeout_ms is None or self._timeout_applied:
            return
        from sqlalchemy import text

        self.session.execute(text(f"SET LOCAL lock_timeout = '{self._lock_timeout_ms}ms'"))
        self._timeout_applied = True

    def _reject(self, exc: Exception, message: str) -> None:
        logger.error("transaction rejected (%s)", type(exc).__name__)
        self.rollback()
        raise ConstraintConflict(message) from exc


def unit_of_work_factory(session_factory, *, lock_timeout_ms: int | None = 3000):
    """Build a factory that opens a new session for each business operation."""

    def factory() -> SqlAlchemyUnitOfWork:
        session = session_factory()
        return SqlAlchemyUnitOfWork(
            session,
            close_session=True,
            lock_timeout_ms=lock_timeout_ms,
        )

    return factory


def repositories_of(uow: SqlAlchemyUnitOfWork) -> Repositories:
    return uow.repositories
