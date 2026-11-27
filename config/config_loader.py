"""YAML and environment-variable configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_DIR.parent

ENV_ALIASES = {
    "dev": "development",
    "development": "development",
    "prod": "production",
    "production": "production",
}

ENV_TO_FILE = {
    "development": "dev.yaml",
    "production": "prod.yaml",
}


def resolve_environment(explicit: str | None = None) -> str:
    """Normalize the active environment name."""
    raw = (explicit or os.getenv("PARKIFY_ENV") or "development").strip().lower()
    return ENV_ALIASES.get(raw, "development")


def _deep_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_origins(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_yaml_config(environment: str) -> dict[str, Any]:
    """Load the YAML configuration file for the given environment."""
    filename = ENV_TO_FILE.get(environment, "dev.yaml")
    config_path = CONFIG_DIR / filename
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration format in {config_path}")
    return data


def apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Overlay environment variables on top of YAML values.

    Sensitive and runtime values are expected from the environment when present.
    """
    app = dict(raw.get("app") or {})
    logging_cfg = dict(raw.get("logging") or {})
    cors = dict(raw.get("cors") or {})
    auth = dict(raw.get("auth") or {})

    if secret := os.getenv("SECRET_KEY"):
        app["secret_key"] = secret
    if host := os.getenv("HOST"):
        app["host"] = host
    if port := os.getenv("PORT"):
        app["port"] = int(port)
    if debug := os.getenv("DEBUG"):
        app["debug"] = _parse_bool(debug)
    if log_level := os.getenv("LOG_LEVEL"):
        logging_cfg["level"] = log_level.upper()
    if cors_origins := os.getenv("CORS_ORIGINS"):
        cors["origins"] = _parse_origins(cors_origins)
    if password_min_length := os.getenv("PASSWORD_MIN_LENGTH"):
        auth["password_min_length"] = password_min_length
    if jwt_secret := os.getenv("JWT_SECRET"):
        auth["jwt_secret"] = jwt_secret
    if jwt_expiration := os.getenv("JWT_EXPIRATION_MINUTES"):
        auth["jwt_expiration_minutes"] = jwt_expiration
    if cookie_secure := os.getenv("COOKIE_SECURE"):
        auth["cookie_secure"] = cookie_secure
    if cookie_samesite := os.getenv("COOKIE_SAMESITE"):
        auth["cookie_samesite"] = cookie_samesite
    if login_max_attempts := os.getenv("LOGIN_MAX_ATTEMPTS"):
        auth["login_max_attempts"] = login_max_attempts
    if login_window := os.getenv("LOGIN_WINDOW_SECONDS"):
        auth["login_window_seconds"] = login_window

    return {
        "app": app,
        "logging": logging_cfg,
        "cors": cors,
        "auth": auth,
        "database_url": os.getenv("DATABASE_URL", "").strip(),
        "raw": raw,
    }


def load_project_env() -> None:
    """Load the repository .env file without overriding variables already set."""
    load_dotenv(PROJECT_ROOT / ".env")


def load_config(environment: str | None = None) -> dict[str, Any]:
    """Load dotenv, YAML config, and environment overrides."""
    load_project_env()
    resolved = resolve_environment(environment)
    yaml_data = load_yaml_config(resolved)
    merged = apply_env_overrides(yaml_data)
    merged["environment"] = resolved
    return merged


def get_nested(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Convenience accessor used by settings construction."""
    return _deep_get(config, *keys, default=default)
