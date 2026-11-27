"""Typed application settings built from YAML and environment variables."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from config.config_loader import load_config
from config.database import normalize_database_url


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for the Flask application."""

    app_name: str
    environment: str
    debug: bool
    host: str
    port: int
    secret_key: str
    log_level: str
    log_format: str
    database_url: str
    cors_origins: list[str] = field(default_factory=list)
    password_min_length: int = 12
    argon2_time_cost: int = 2
    argon2_memory_kib: int = 19456
    argon2_parallelism: int = 1
    jwt_secret: str = ""
    jwt_expiration_minutes: int = 60
    cookie_secure: bool = False
    cookie_samesite: str = "Lax"
    login_max_attempts: int = 5
    login_window_seconds: int = 900

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def build_settings(environment: str | None = None) -> Settings:
    """Construct a Settings instance for the requested environment."""
    config = load_config(environment)
    app = config.get("app") or {}
    logging_cfg = config.get("logging") or {}
    cors = config.get("cors") or {}

    origins = cors.get("origins") or []
    if isinstance(origins, str):
        origins = [item.strip() for item in origins.split(",") if item.strip()]

    auth = config.get("auth") or {}
    return Settings(
        app_name=str(app.get("name") or "Parkify"),
        environment=str(config.get("environment") or "development"),
        debug=bool(app.get("debug", False)),
        host=str(app.get("host") or "127.0.0.1"),
        port=int(app.get("port") or 5001),
        secret_key=str(app.get("secret_key") or "change-me"),
        log_level=str(logging_cfg.get("level") or "INFO").upper(),
        log_format=str(
            logging_cfg.get("format")
            or "%(asctime)s | %(levelname)-8s | %(name)s | %(request_id)s | %(message)s"
        ),
        database_url=normalize_database_url(str(config.get("database_url") or "")),
        cors_origins=list(origins),
        password_min_length=_bounded_int(
            auth.get("password_min_length", 12),
            "password_min_length",
            minimum=8,
            maximum=128,
        ),
        argon2_time_cost=_bounded_int(
            auth.get("argon2_time_cost", 2),
            "argon2_time_cost",
            minimum=1,
            maximum=10,
        ),
        argon2_memory_kib=_bounded_int(
            auth.get("argon2_memory_kib", 19456),
            "argon2_memory_kib",
            minimum=8192,
            maximum=1_048_576,
        ),
        argon2_parallelism=_bounded_int(
            auth.get("argon2_parallelism", 1),
            "argon2_parallelism",
            minimum=1,
            maximum=8,
        ),
        jwt_secret=_jwt_secret(str(auth.get("jwt_secret") or ""), environment=str(config.get("environment") or "development")),
        jwt_expiration_minutes=_bounded_int(
            auth.get("jwt_expiration_minutes", 60),
            "jwt_expiration_minutes",
            minimum=5,
            maximum=720,
        ),
        cookie_secure=_cookie_secure(auth.get("cookie_secure", False), environment=str(config.get("environment") or "development")),
        cookie_samesite=_cookie_samesite(
            str(auth.get("cookie_samesite") or "Lax"),
            secure=_cookie_secure(auth.get("cookie_secure", False), environment=str(config.get("environment") or "development")),
        ),
        login_max_attempts=_bounded_int(
            auth.get("login_max_attempts", 5),
            "login_max_attempts",
            minimum=1,
            maximum=50,
        ),
        login_window_seconds=_bounded_int(
            auth.get("login_window_seconds", 900),
            "login_window_seconds",
            minimum=60,
            maximum=86_400,
        ),
    )


def _jwt_secret(value: str, *, environment: str) -> str:
    secret = value.strip()
    placeholders = {
        "",
        "change-me",
        "change-me-in-production",
        "dev-only-jwt-secret-change-me",
        "dev-only-jwt-secret-change-me-local",
    }
    if environment == "production" and (secret in placeholders or len(secret) < 32):
        raise ValueError("Set JWT_SECRET to a long random value before running in production.")
    if len(secret) < 16:
        raise ValueError("JWT secret must be at least 16 characters.")
    return secret


def _cookie_secure(value: object, *, environment: str) -> bool:
    if isinstance(value, str):
        secure = value.strip().lower() in {"1", "true", "yes", "on"}
    else:
        secure = bool(value)
    if environment == "production" and not secure:
        raise ValueError("Production session cookies must be Secure.")
    return secure


def _cookie_samesite(value: str, *, secure: bool) -> str:
    cleaned = value.strip().title()
    if cleaned not in {"Lax", "Strict", "None"}:
        raise ValueError("cookie_samesite must be Lax, Strict, or None.")
    if cleaned == "None" and not secure:
        raise ValueError("SameSite=None cookies must be Secure.")
    return cleaned


def _bounded_int(value: object, label: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a whole number.")
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return parsed


@lru_cache(maxsize=4)
def get_settings(environment: str | None = None) -> Settings:
    """Return cached settings for the given environment key."""
    return build_settings(environment)
