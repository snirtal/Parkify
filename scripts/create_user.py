"""Create one Parkify operator from the command line.

There is no public registration. The password is prompted and is not shown.

    .venv/bin/python scripts/create_user.py --email name@example.com --full-name "Ada Admin" --role admin

The command uses DATABASE_URL. It does not print the password or its hash.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.config_loader import load_project_env
from config.database import normalize_database_url
from config.settings import get_settings
from services.exceptions import DomainError
from services.factory import build_services
from services.passwords import Argon2PasswordHasher
from services.results import UserAccount
from services.unit_of_work import SqlAlchemyUnitOfWork
from services.users import USER_ROLES, UserService
from utils.logging_setup import setup_logging

logger = logging.getLogger("parkify.users.cli")
PasswordReader = Callable[[str], str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Parkify operator. There is no public registration."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--role", required=True, choices=sorted(USER_ROLES))
    return parser


def read_password(reader: PasswordReader = getpass.getpass) -> str:
    """Ask for the password twice. Nothing typed is displayed."""
    password = reader("Password: ")
    if password == "":
        raise SystemExit("Password is required.")
    confirmation = reader("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    return password


def success_message(account: UserAccount) -> str:
    return f"Created user {account.id} role={account.role}"


def execute(args: argparse.Namespace, reader: PasswordReader, service: UserService) -> UserAccount:
    password = read_password(reader)
    return service.create_user(
        email=args.email,
        full_name=args.full_name,
        password=password,
        role=args.role,
    )


def main(argv: list[str] | None = None) -> int:
    load_project_env()
    settings = get_settings()
    setup_logging(settings)
    if not settings.database_url:
        print("DATABASE_URL is not configured.", file=sys.stderr)
        return 1
    args = build_parser().parse_args(argv)
    engine = create_engine(normalize_database_url(settings.database_url))
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory(), close_session=True)

    service = build_services(
        uow_factory,
        passwords=Argon2PasswordHasher.from_settings(settings),
        password_min_length=settings.password_min_length,
    ).users
    try:
        account = execute(args, getpass.getpass, service)
    except DomainError as exc:
        logger.info("create user rejected code=%s", exc.code)
        print(exc.message, file=sys.stderr)
        return 2
    except Exception as exc:
        logger.error("create user failed (%s)", type(exc).__name__)
        print(f"Could not create the user ({type(exc).__name__}).", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print(success_message(account))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
