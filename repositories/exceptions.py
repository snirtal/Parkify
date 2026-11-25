"""Repository errors.

Messages stay generic so connection strings and credentials are never included.
"""

from __future__ import annotations


class RepositoryError(Exception):
    """A data-access operation failed."""
