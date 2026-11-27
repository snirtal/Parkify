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


class AuthenticationError(DomainError):
    """The caller is not signed in, or the credentials are not valid."""

    status_code = 401

    def __init__(self, message: str, *, code: str = "unauthenticated") -> None:
        super().__init__(message, code=code)


class InactiveAccountError(AuthenticationError):
    """The password matched an account that is not allowed to sign in."""

    status_code = 403

    def __init__(self, message: str = "This account is inactive.", *, code: str = "account_inactive") -> None:
        super().__init__(message, code=code)


class CsrfError(DomainError):
    """A cookie-authenticated change did not include the matching CSRF token."""

    status_code = 403

    def __init__(self, message: str = "The security token is missing or invalid.", *, code: str = "csrf_failed") -> None:
        super().__init__(message, code=code)


class RateLimitError(DomainError):
    """Too many attempts in the configured window."""

    status_code = 429

    def __init__(self, message: str = "Too many sign-in attempts. Try again later.", *, code: str = "rate_limited") -> None:
        super().__init__(message, code=code)
