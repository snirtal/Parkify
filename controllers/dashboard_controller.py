"""Facility dashboard snapshot."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.dependencies import current_services
from controllers.parsing import identifier, query_int
from controllers.serialization import dump

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/facilities/<facility_id>")


@dashboard_bp.get("/dashboard")
def get_dashboard(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    recent_limit = query_int("recent_limit", default=6, minimum=1, maximum=100)
    snapshot = current_services().dashboard.snapshot(facility_id, recent_limit=recent_limit)
    return jsonify(dump(snapshot)), 200
