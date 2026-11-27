"""Facility dashboard snapshot."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.authorization import current_account, permission_required
from controllers.dependencies import current_services
from controllers.parsing import identifier, query_int
from controllers.presentation import omit_financial_fields
from controllers.serialization import dump
from services.permissions import OCCUPANCY_READ, PRICING_READ, allows

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/facilities/<facility_id>")


@dashboard_bp.get("/dashboard")
@permission_required(OCCUPANCY_READ)
def get_dashboard(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    recent_limit = query_int("recent_limit", default=6, minimum=1, maximum=100)
    snapshot = current_services().dashboard.snapshot(facility_id, recent_limit=recent_limit)
    payload = dump(snapshot)
    if not allows(current_account().role, PRICING_READ):
        payload = omit_financial_fields(payload)
    return jsonify(payload), 200
