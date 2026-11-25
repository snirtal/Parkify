"""Tests for the health-check endpoint."""

from __future__ import annotations


def test_health_endpoint_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.content_type.startswith("application/json")

    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "Parkify"
    assert payload["environment"] == "development"
    assert payload["version"] == "0.1.0"


def test_health_endpoint_rejects_unsupported_methods(client):
    response = client.post("/api/health")

    assert response.status_code == 405
    payload = response.get_json()
    assert "error" in payload
    assert payload["error"]["code"] == "method_not_allowed"
    assert "message" in payload["error"]
