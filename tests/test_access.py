"""Admin, employee, and anonymous access to business endpoints."""

from __future__ import annotations

import logging

import pytest

from config.facility import DEFAULT_FACILITY_ID
from tests.http_auth import operator_client

FACILITY = f"/api/facilities/{DEFAULT_FACILITY_ID}"
FINANCIAL = ("hourly_rate", "daily_max_rate", "ev_surcharge", "amount", "daily_maximum", "quote")


@pytest.fixture()
def employee_client(db_session):
    return operator_client(db_session, role="employee", email="employee@parkify.test")


def test_anonymous_business_requests_are_unauthorized(client):
    spots = client.get(f"{FACILITY}/spots")
    settings = client.get(f"{FACILITY}/settings")
    entry = client.post(f"{FACILITY}/entries", json={"plate_number": "API-100", "spot_code": "P-210"})
    health = client.get("/api/health")

    assert spots.status_code == settings.status_code == entry.status_code == 401
    assert spots.get_json()["error"]["code"] == "unauthenticated"
    assert health.status_code == 200


def test_admin_can_read_rates_and_change_the_facility(api_client):
    spot = api_client.get(f"{FACILITY}/spots/P-210")
    assert spot.status_code == 200
    assert spot.get_json()["hourly_rate"] == "3.50"
    assert api_client.get(f"{FACILITY}/settings").status_code == 200
    assert api_client.get(f"{FACILITY}/sessions").status_code == 200

    blocked = api_client.post(
        f"{FACILITY}/entries",
        json={"plate_number": "API-100", "spot_code": "P-210"},
        headers={"X-CSRF-Token": "not-the-cookie"},
    )
    assert blocked.status_code == 403
    assert blocked.get_json()["error"]["code"] == "csrf_failed"


def test_employee_can_read_occupancy_without_financial_fields(employee_client):
    occupancy = employee_client.get(f"{FACILITY}/occupancy")
    spot = employee_client.get(f"{FACILITY}/spots/P-210")
    dashboard = employee_client.get(f"{FACILITY}/dashboard")
    series = employee_client.get(
        f"{FACILITY}/analytics/occupancy?start=2026-11-25T14:00:00&end=2026-11-25T15:00:00"
    )

    assert occupancy.status_code == spot.status_code == dashboard.status_code == series.status_code == 200
    assert occupancy.get_json()["counts"]["total"] == 24
    assert spot.get_json()["status"] == "available"
    assert dashboard.get_json()["counts"]["occupied"] == 14
    combined = occupancy.get_data(as_text=True) + spot.get_data(as_text=True) + dashboard.get_data(as_text=True)
    for field in FINANCIAL:
        assert field not in combined


def test_employee_is_denied_restricted_endpoints(employee_client, caplog):
    caplog.set_level(logging.INFO)
    denied = {
        "settings": employee_client.get(f"{FACILITY}/settings"),
        "sessions": employee_client.get(f"{FACILITY}/sessions"),
        "quotes": employee_client.post(
            f"{FACILITY}/quotes",
            json={
                "spot_code": "P-210",
                "started_at": "2026-11-25T14:24:00",
                "ended_at": "2026-11-25T16:24:00",
            },
        ),
        "entries": employee_client.post(
            f"{FACILITY}/entries",
            json={"plate_number": "API-100", "spot_code": "P-210"},
        ),
        "reservations": employee_client.get(f"{FACILITY}/reservations"),
        "activity": employee_client.get(f"{FACILITY}/gate-activity"),
    }
    assert {response.status_code for response in denied.values()} == {403}
    assert {response.get_json()["error"]["code"] for response in denied.values()} == {"forbidden"}
    logged = caplog.text
    assert "authorization denied role=employee" in logged
    assert "correct-horse-battery" not in logged
    assert "password_hash" not in logged
