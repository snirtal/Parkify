"""Tests for centralized JSON error handling."""

from __future__ import annotations

from utils.errors import AppError


def test_unknown_route_returns_json_not_found(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.content_type.startswith("application/json")

    payload = response.get_json()
    assert payload["error"]["code"] == "not_found"
    assert "message" in payload["error"]


def test_app_error_returns_consistent_json_payload(app, client):
    @app.get("/api/test/app-error")
    def raise_app_error():
        raise AppError(
            "Simulated validation failure",
            code="validation_error",
            status_code=422,
            details={"field": "plateNumber"},
        )

    response = client.get("/api/test/app-error")

    assert response.status_code == 422
    payload = response.get_json()
    assert payload == {
        "error": {
            "code": "validation_error",
            "message": "Simulated validation failure",
            "details": {"field": "plateNumber"},
        }
    }


def test_unexpected_exception_returns_internal_server_error(app, client):
    @app.get("/api/test/boom")
    def raise_unexpected():
        raise RuntimeError("boom")

    response = client.get("/api/test/boom")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["error"]["code"] == "internal_server_error"
    assert payload["error"]["message"] == "An unexpected error occurred."
