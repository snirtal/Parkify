"""Historical occupancy and the current floor and zone breakdown."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.dependencies import current_services
from controllers.parsing import identifier, query_int, query_timestamp
from controllers.serialization import dump

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/facilities/<facility_id>")


@analytics_bp.get("/analytics/occupancy")
def occupancy_over_time(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    start = query_timestamp("start", required=True)
    end = query_timestamp("end", required=True)
    bucket_minutes = query_int("bucket_minutes", default=60, minimum=15, maximum=1440)
    assert start is not None and end is not None
    series = current_services().analytics.occupancy_over_time(
        facility_id,
        start,
        end,
        bucket_minutes=bucket_minutes,
    )
    return jsonify(dump(series)), 200


@analytics_bp.get("/analytics/floors")
def occupancy_by_floor(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    floors = current_services().analytics.occupancy_by_floor(facility_id)
    return jsonify({"items": dump(floors)}), 200


@analytics_bp.get("/analytics/zones")
def occupancy_by_zone(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    zones = current_services().analytics.occupancy_by_zone(facility_id)
    return jsonify({"items": dump(zones)}), 200
