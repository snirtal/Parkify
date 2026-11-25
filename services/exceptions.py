"""Domain errors raised by services.

Messages describe the business rejection. They never include connection
strings, SQL, or other credentials.
"""

from __future__ import annotations


class DomainError(Exception):
    """A business rule rejected the operation."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationError(DomainError):
    """The supplied values are not usable."""

    def __init__(self, message: str, *, code: str = "validation_error") -> None:
        super().__init__(message, code=code)


class NotFoundError(DomainError):
    """The requested facility record does not exist."""

    def __init__(self, message: str, *, code: str = "not_found") -> None:
        super().__init__(message, code=code)


class ConflictError(DomainError):
    """The operation conflicts with the current facility state."""

    def __init__(self, message: str, *, code: str = "conflict") -> None:
        super().__init__(message, code=code)


class ConstraintConflict(ConflictError):
    """The database rejected a write that the pre-check did not catch."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="constraint_conflict")
