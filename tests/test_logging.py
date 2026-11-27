"""Logging tests that do not use a database."""

from __future__ import annotations

import logging

from config.settings import Settings, get_settings
from scripts.live_parking_simulator import summarize_tick
from utils.logging_setup import redact, setup_logging
from utils.request_logging import REQUEST_ID_HEADER


def _settings(level: str) -> Settings:
    return Settings(
        app_name="Parkify",
        environment="development",
        debug=False,
        host="127.0.0.1",
        port=5001,
        secret_key="test-secret",
        log_level=level,
        log_format="%(levelname)s | %(request_id)s | %(message)s",
        database_url="",
        cors_origins=[],
    )


def test_request_id_is_logged_without_the_query_string(client, caplog):
    caplog.set_level(logging.INFO)
    logging.getLogger().addHandler(caplog.handler)
    try:
        response = client.get(
            "/api/health?query=VEL-204X",
            headers={REQUEST_ID_HEADER: "req-12345678"},
        )
    finally:
        logging.getLogger().removeHandler(caplog.handler)

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-12345678"
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "request_id=req-12345678" in messages
    assert "path=/api/health" in messages
    assert "VEL-204X" not in messages
    assert "query=" not in messages


def test_unsafe_request_id_is_replaced(client):
    response = client.get("/api/health", headers={REQUEST_ID_HEADER: "bad id"})

    request_id = response.headers[REQUEST_ID_HEADER]
    assert request_id != "bad id"
    assert len(request_id) == 32


def test_log_text_redacts_urls_and_passwords():
    cleaned = redact(
        "connect postgresql://user:secret@ep-example.neon.tech/parkify password=hunter2"
    )
    assert "secret@" not in cleaned
    assert "hunter2" not in cleaned
    assert "[redacted-url]" in cleaned
    assert "password=[redacted]" in cleaned


def test_log_level_comes_from_settings():
    try:
        setup_logging(_settings("WARNING"))
        assert logging.getLogger().level == logging.WARNING
        assert logging.getLogger("parkify").level == logging.WARNING
    finally:
        setup_logging(get_settings())


def test_simulator_summary_omits_license_plates():
    entry = summarize_tick("2026-11-25 14:29", "entry", spot="P-210", status=201)
    rejected = summarize_tick(
        "2026-11-25 14:29",
        "entry_rejected",
        spot="P-210",
        status=409,
        code="spot_occupied",
    )

    assert "spot=P-210" in entry
    assert "LXK-482M" not in entry
    assert "LXK-482M" not in rejected
    assert "code=spot_occupied" in rejected
