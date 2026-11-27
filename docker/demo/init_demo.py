"""Initialize the local Docker demo database.

This process refuses every database that is not the Compose service named
postgres. It does not read .env and it does not log passwords, hashes, or
connection strings.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

APP_ROOT = Path("/app")
if APP_ROOT.is_dir() and str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

logger = logging.getLogger("parkify.demo")


def configure_logging() -> None:
    """Send demo logs to stderr and strip connection strings."""
    from utils.logging_setup import RedactingFormatter

    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.getLogger("parkify").setLevel(logging.INFO)

DEMO_HOST = "postgres"
DEMO_DATABASE = "parkify"
DEMO_USER = "parkify"
FACILITY_ID = "facility-skyline"


@dataclass(frozen=True)
class DemoAccount:
    email: str
    full_name: str
    password: str
    role: str


DEMO_ACCOUNTS = (
    DemoAccount("admin@parkify.demo", "Demo Admin", "Demo-Admin-Pass1", "admin"),
    DemoAccount("employee@parkify.demo", "Demo Employee", "Demo-Employee-Pass1", "employee"),
    DemoAccount("simulator@parkify.demo", "Demo Simulator", "Demo-Simulator-Pass1", "simulator"),
)


def assert_demo_database(url: str) -> None:
    """Allow only the local Compose database with SSL disabled."""
    if not isinstance(url, str) or not url.strip():
        raise SystemExit("Demo init refuses to run: DATABASE_URL is not set.")
    if "neon.tech" in url.lower():
        raise SystemExit("Demo init refuses to run: this database is not the local demo.")
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    name = parts.path.strip("/")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if (
        host != DEMO_HOST
        or name != DEMO_DATABASE
        or (parts.username or "") != DEMO_USER
        or query.get("sslmode") != "disable"
    ):
        raise SystemExit("Demo init refuses to run: this database is not the local demo.")


def should_seed(facility_exists: bool) -> bool:
    """Seed only an empty demo. Later runs must leave operator data alone."""
    return not facility_exists


def ensure_demo_users(
    lookup: Callable[[str], object | None],
    create: Callable[[DemoAccount], None],
) -> tuple[int, int]:
    """Create each demo account once. Existing users and passwords stay as they are."""
    created = 0
    present = 0
    for account in DEMO_ACCOUNTS:
        if lookup(account.email) is not None:
            present += 1
            logger.info("demo user already present role=%s", account.role)
            continue
        create(account)
        created += 1
        logger.info("demo user created role=%s", account.role)
    return created, present


def main() -> int:
    url = os.environ.get("DATABASE_URL", "")
    assert_demo_database(url)
    os.environ["DATABASE_URL"] = url.strip()
    os.environ["MIGRATION_DATABASE_URL"] = url.strip()

    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import sessionmaker

    from config.database import create_db_engine
    from config.settings import get_settings
    from models.orm import Facility
    from repositories.seed import seed_database
    from services.exceptions import ConflictError
    from services.factory import build_services
    from services.passwords import Argon2PasswordHasher
    from services.support import run_in_transaction
    from services.unit_of_work import SqlAlchemyUnitOfWork

    configure_logging()
    try:
        get_settings.cache_clear()
        settings = get_settings()
        logger.info("demo migration started")
        command.upgrade(Config("alembic.ini"), "head")
        configure_logging()
        logger.info("demo migration finished")

        engine = create_db_engine(settings.database_url)
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
        with factory() as session:
            exists = session.get(Facility, FACILITY_ID) is not None
        if should_seed(exists):
            with factory() as session:
                seed_database(session)
            logger.info("demo facility seeded")
        else:
            logger.info("demo facility already present")

        def uow_factory() -> SqlAlchemyUnitOfWork:
            return SqlAlchemyUnitOfWork(factory(), close_session=True)

        users = build_services(
            uow_factory,
            passwords=Argon2PasswordHasher.from_settings(settings),
            password_min_length=settings.password_min_length,
        ).users

        def lookup(email: str) -> object | None:
            return run_in_transaction(
                uow_factory,
                lambda uow: uow.repositories.users.get_by_email(email),
            )

        def create(account: DemoAccount) -> None:
            try:
                users.create_user(
                    email=account.email,
                    full_name=account.full_name,
                    password=account.password,
                    role=account.role,
                )
            except ConflictError:
                logger.info("demo user already present role=%s", account.role)

        created, present = ensure_demo_users(lookup, create)
        logger.info("demo users ready created=%s present=%s", created, present)
        engine.dispose()
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("demo init failed error=%s", type(exc).__name__)
        print(f"Demo initialization failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    logger.info("demo initialization complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
