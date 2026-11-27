"""API tests against the isolated Neon branch.

Writes stay inside the rolled-back test transaction.
"""

from __future__ import annotations

from config.facility import DEFAULT_FACILITY_ID

FACILITY = f"/api/facilities/{DEFAULT_FACILITY_ID}"


def test_read_endpoints_match_the_seeded_snapshot(api_client) -> None:
    spots = api_client.get(f"{FACILITY}/spots?query=vel-204x&status=occupied")
    assert spots.status_code == 200
    assert [item["code"] for item in spots.get_json()["items"]] == ["P-204"]

    spot = api_client.get(f"{FACILITY}/spots/P-210")
    assert spot.status_code == 200
    body = spot.get_json()
    assert body["status"] == "available"
    assert body["hourly_rate"] == "3.50"

    missing_spot = api_client.get(f"{FACILITY}/spots/P-999")
    assert missing_spot.status_code == 404
    assert missing_spot.get_json()["error"]["code"] == "not_found"

    occupancy = api_client.get(f"{FACILITY}/occupancy").get_json()
    counts = occupancy["counts"]
    assert (
        counts["total"],
        counts["available"],
        counts["occupied"],
        counts["reserved"],
        counts["unavailable"],
    ) == (24, 6, 14, 2, 2)
    assert counts["occupancy_percentage"] == "58.3"

    sessions = api_client.get(f"{FACILITY}/sessions")
    assert sessions.status_code == 200
    assert len(sessions.get_json()["items"]) == 14

    dashboard = api_client.get(f"{FACILITY}/dashboard").get_json()
    assert dashboard["active_sessions"] == 14
    assert dashboard["overstay_sessions"] == 1
    assert dashboard["recent_gate_activity"][0]["id"] == "gl-1"
    assert dashboard["counts"]["occupancy_percentage"] == "58.3"

    activity = api_client.get(f"{FACILITY}/gate-activity?limit=1&offset=0")
    page = activity.get_json()
    assert activity.status_code == 200
    assert len(page["items"]) == 1
    assert page["total"] == 6
    assert page["limit"] == 1
    empty_page = api_client.get(f"{FACILITY}/gate-activity?limit=1&offset=6").get_json()
    assert empty_page["items"] == []
    assert empty_page["total"] == 6

    series = api_client.get(
        f"{FACILITY}/analytics/occupancy?start=2026-11-25T14:00:00&end=2026-11-25T15:00:00"
    ).get_json()
    assert series["has_history"] is True
    assert series["points"][0]["occupied"] == 12
    future = api_client.get(
        f"{FACILITY}/analytics/occupancy?start=2026-11-25T18:00:00&end=2026-11-25T19:00:00"
    ).get_json()
    assert future["has_history"] is False
    assert future["points"] == []

    floors = api_client.get(f"{FACILITY}/analytics/floors").get_json()["items"]
    zones = api_client.get(f"{FACILITY}/analytics/zones").get_json()["items"]
    assert sum(item["capacity"] for item in floors) == 24
    assert sum(item["occupied"] for item in zones) == 14

    settings = api_client.get(f"{FACILITY}/settings")
    assert settings.status_code == 200
    assert settings.get_json()["hourly_rate"] == "4.20"
    assert settings.get_json()["grace_period_minutes"] == 15

    missing = api_client.get("/api/facilities/facility-missing/dashboard")
    assert missing.status_code == 404
    assert "postgresql" not in missing.get_data(as_text=True).lower()
    assert "Traceback" not in missing.get_data(as_text=True)


def test_entry_exit_quote_and_settings_rollback(api_client) -> None:
    entered = api_client.post(
        f"{FACILITY}/entries",
        json={"plate_number": "API-100", "spot_code": "P-210"},
    )
    assert entered.status_code == 201
    entry = entered.get_json()
    assert entry["session"]["status"] == "Active"
    assert entry["session"]["spot_code"] == "P-210"
    assert entry["gate_event"]["direction"] == "entry"
    assert entry["quote"] is None

    conflict = api_client.post(
        f"{FACILITY}/entries",
        json={"plate_number": "API-101", "spot_code": "P-210"},
    )
    assert conflict.status_code == 409
    assert conflict.get_json()["error"]["code"] == "spot_occupied"

    left = api_client.post(f"{FACILITY}/exits", json={"plate_number": "API-100"})
    assert left.status_code == 200
    exit_body = left.get_json()
    assert exit_body["session"]["status"] == "Completed"
    assert exit_body["gate_event"]["direction"] == "exit"
    assert exit_body["quote"]["amount"] == "0.00"

    quote = api_client.post(
        f"{FACILITY}/quotes",
        json={
            "spot_code": "P-210",
            "started_at": "2026-11-25T14:24:00",
            "ended_at": "2026-11-25T16:24:00",
        },
    )
    assert quote.status_code == 200
    assert quote.get_json()["amount"] == "7.00"
    assert quote.get_json()["hourly_rate"] == "3.50"

    updated = api_client.patch(f"{FACILITY}/settings", json={"grace_period_minutes": 21})
    assert updated.status_code == 200
    assert updated.get_json()["grace_period_minutes"] == 21

    rejected = api_client.patch(f"{FACILITY}/settings", json={"hourly_rate": "0.00"})
    assert rejected.status_code == 400
    assert rejected.get_json()["error"]["code"] == "validation_error"

    current = api_client.get(f"{FACILITY}/settings").get_json()
    assert current["grace_period_minutes"] == 21
    assert current["hourly_rate"] == "4.20"


def test_reservation_conflict_update_and_cancel(api_client) -> None:
    overlap = api_client.post(
        f"{FACILITY}/reservations",
        json={
            "plate_number": "API-300",
            "spot_code": "P-203",
            "starts_at": "2026-11-25T14:00:00",
            "ends_at": "2026-11-25T16:00:00",
        },
    )
    assert overlap.status_code == 409
    assert overlap.get_json()["error"]["code"] == "reservation_overlap"

    created = api_client.post(
        f"{FACILITY}/reservations",
        json={
            "plate_number": "API-200",
            "spot_code": "P-210",
            "starts_at": "2026-11-26T09:00:00",
            "ends_at": "2026-11-26T11:00:00",
            "driver_name": "Api Driver",
        },
    )
    assert created.status_code == 201
    reservation = created.get_json()
    assert reservation["effective_status"] == "Scheduled"
    assert reservation["spot_code"] == "P-210"

    fetched = api_client.get(f"{FACILITY}/reservations/{reservation['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json()["plate_number"] == "API-200"

    listed = api_client.get(f"{FACILITY}/reservations?status=Scheduled&spot_code=P-210")
    assert any(item["id"] == reservation["id"] for item in listed.get_json()["items"])

    changed = api_client.patch(
        f"{FACILITY}/reservations/{reservation['id']}",
        json={"ends_at": "2026-11-26T12:00:00"},
    )
    assert changed.status_code == 200
    assert changed.get_json()["ends_at"] == "2026-11-26T12:00:00"

    cancelled = api_client.post(f"{FACILITY}/reservations/{reservation['id']}/cancellation")
    assert cancelled.status_code == 200
    assert cancelled.get_json()["status"] == "Cancelled"

    missing = api_client.get(f"{FACILITY}/reservations/res-missing")
    assert missing.status_code == 404

    lifecycle = api_client.post(f"{FACILITY}/reservations/lifecycle")
    assert lifecycle.status_code == 200
    assert isinstance(lifecycle.get_json()["items"], list)
