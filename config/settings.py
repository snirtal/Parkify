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
    )


@lru_cache(maxsize=4)
def get_settings(environment: str | None = None) -> Settings:
    """Return cached settings for the given environment key."""
    return build_settings(environment)
