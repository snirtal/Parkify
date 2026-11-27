"""Historical occupancy and the current floor and zone breakdown."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.authorization import current_account, permission_required
from controllers.dependencies import current_services
from controllers.parsing import identifier, query_int, query_timestamp
from controllers.presentation import omit_financial_fields
from controllers.serialization import dump
from services.permissions import OCCUPANCY_READ, PRICING_READ, allows

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/facilities/<facility_id>")


@analytics_bp.get("/analytics/occupancy")
@permission_required(OCCUPANCY_READ)
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
    return jsonify(_visible(dump(series))), 200


@analytics_bp.get("/analytics/floors")
@permission_required(OCCUPANCY_READ)
def occupancy_by_floor(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    floors = current_services().analytics.occupancy_by_floor(facility_id)
    return jsonify(_visible({"items": dump(floors)})), 200


@analytics_bp.get("/analytics/zones")
@permission_required(OCCUPANCY_READ)
def occupancy_by_zone(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    zones = current_services().analytics.occupancy_by_zone(facility_id)
    return jsonify(_visible({"items": dump(zones)})), 200


def _visible(payload: dict) -> dict:
    if allows(current_account().role, PRICING_READ):
        return payload
    return omit_financial_fields(payload)
