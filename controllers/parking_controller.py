"""Parking spot and occupancy endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.dependencies import current_services
from controllers.parsing import identifier, query_choice, query_text
from controllers.serialization import dump
from services.rules import SPOT_STATUSES
from utils.errors import AppError

BAY_CLASSES = ("Standard", "EV Fast 150kW", "VIP Priority", "Accessible")

parking_bp = Blueprint("parking", __name__, url_prefix="/api/facilities/<facility_id>")


@parking_bp.get("/spots")
def list_spots(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    floor_id = query_text("floor_id", maximum=64)
    floor_code = query_text("floor_code", maximum=16)
    zone_id = query_text("zone_id", maximum=64)
    zone_code = query_text("zone_code", maximum=16)
    status = query_choice("status", SPOT_STATUSES)
    bay_class = query_choice("bay_class", BAY_CLASSES)
    query = query_text("query", maximum=32)
    spots = current_services().parking.search_spots(
        facility_id,
        floor_id=floor_id,
        floor_code=floor_code,
        zone_id=zone_id,
        zone_code=zone_code,
        status=status,
        bay_class=bay_class,
        query=query,
    )
    return jsonify({"items": dump(spots)}), 200


@parking_bp.get("/spots/<spot_code>")
def get_spot(facility_id: str, spot_code: str):
    facility_id = identifier(facility_id, "facility_id")
    spot_code = identifier(spot_code, "spot_code", maximum=16)
    matches = current_services().parking.search_spots(facility_id, query=spot_code)
    found = next((spot for spot in matches if spot.code == spot_code.upper()), None)
    if found is None:
        raise AppError("Parking spot was not found in this facility.", code="not_found", status_code=404)
    return jsonify(dump(found)), 200


@parking_bp.get("/occupancy")
def get_occupancy(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    occupancy = current_services().parking.summarize(facility_id)
    return jsonify(dump(occupancy)), 200
