"""Controller checks for a signed-in admin. Anonymous callers are rejected first."""

from __future__ import annotations

from config.facility import DEFAULT_FACILITY_ID

FACILITY = f"/api/facilities/{DEFAULT_FACILITY_ID}"


def test_invalid_query_status_is_400(api_client):
    response = api_client.get(f"{FACILITY}/spots?status=nope")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_invalid_pagination_is_400(api_client):
    response = api_client.get(f"{FACILITY}/gate-activity?limit=0")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_missing_json_fields_are_400(api_client):
    response = api_client.post(f"{FACILITY}/entries", json={})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_non_json_body_is_400(api_client):
    response = api_client.post(
        f"{FACILITY}/reservations",
        data="plate_number=ABC",
        content_type="text/plain",
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"]
    assert "Traceback" not in response.get_data(as_text=True)


def test_timezone_timestamp_is_rejected(api_client):
    response = api_client.post(
        f"{FACILITY}/quotes",
        json={
            "spot_code": "P-210",
            "started_at": "2026-11-25T14:24:00Z",
            "ended_at": "2026-11-25T16:24:00",
        },
    )

    assert response.status_code == 400
    assert "time zone" in response.get_json()["error"]["message"]


def test_float_money_is_rejected(api_client):
    response = api_client.patch(f"{FACILITY}/settings", json={"hourly_rate": 4.2})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_analytics_range_is_required(api_client):
    response = api_client.get(f"{FACILITY}/analytics/occupancy")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_unsupported_method_is_405(client):
    response = client.post(f"{FACILITY}/dashboard")

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "method_not_allowed"


def test_exit_requires_a_vehicle_or_session(api_client):
    response = api_client.post(f"{FACILITY}/exits", json={})

    assert response.status_code == 400
    assert "plate_number or session_id" in response.get_json()["error"]["message"]
