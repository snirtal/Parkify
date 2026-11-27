"""Price a stay without creating a session or storing the charge."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.authorization import permission_required
from controllers.dependencies import current_services
from controllers.parsing import identifier, json_object, required_text, required_timestamp
from controllers.serialization import dump
from services.permissions import PRICING_QUOTE

pricing_bp = Blueprint("pricing", __name__, url_prefix="/api/facilities/<facility_id>")


@pricing_bp.post("/quotes")
@permission_required(PRICING_QUOTE)
def quote_stay(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    payload = json_object()
    spot_code = required_text(payload, "spot_code", maximum=16)
    started_at = required_timestamp(payload, "started_at")
    ended_at = required_timestamp(payload, "ended_at")
    quote = current_services().parking.quote_stay(
        facility_id,
        spot_code,
        started_at,
        ended_at,
    )
    return jsonify(dump(quote)), 200
