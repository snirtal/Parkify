"""Data-access layer.

Repositories stage changes on a SQLAlchemy session and never commit it.
repositories.seed loads the facility snapshot.
"""

from repositories.factory import Repositories, build_repositories

__all__ = ["Repositories", "build_repositories"]
