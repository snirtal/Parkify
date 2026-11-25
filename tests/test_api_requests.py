"""Controller checks that fail before a service or database call."""

from __future__ import annotations

FACILITY = "/api/facilities/facility-skyline"


def test_invalid_query_status_is_400(client):
    response = client.get(f"{FACILITY}/spots?status=nope")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_invalid_pagination_is_400(client):
    response = client.get(f"{FACILITY}/gate-activity?limit=0")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_missing_json_fields_are_400(client):
    response = client.post(f"{FACILITY}/entries", json={})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_non_json_body_is_400(client):
    response = client.post(
        f"{FACILITY}/reservations",
        data="plate_number=ABC",
        content_type="text/plain",
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"]
    assert "Traceback" not in response.get_data(as_text=True)


def test_timezone_timestamp_is_rejected(client):
    response = client.post(
        f"{FACILITY}/quotes",
        json={
            "spot_code": "P-210",
            "started_at": "2026-11-25T14:24:00Z",
            "ended_at": "2026-11-25T16:24:00",
        },
    )

    assert response.status_code == 400
    assert "time zone" in response.get_json()["error"]["message"]


def test_float_money_is_rejected(client):
    response = client.patch(f"{FACILITY}/settings", json={"hourly_rate": 4.2})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_analytics_range_is_required(client):
    response = client.get(f"{FACILITY}/analytics/occupancy")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_unsupported_method_is_405(client):
    response = client.post(f"{FACILITY}/dashboard")

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "method_not_allowed"


def test_exit_requires_a_vehicle_or_session(client):
    response = client.post(f"{FACILITY}/exits", json={})

    assert response.status_code == 400
    assert "plate_number or session_id" in response.get_json()["error"]["message"]
