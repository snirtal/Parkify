"""Repository errors.

Messages stay generic so connection strings and credentials are never included.
"""

from __future__ import annotations


class RepositoryError(Exception):
    """A data-access operation failed."""


class RepositoryConflict(RepositoryError):
    """A row lock was not granted before the lock timeout."""
