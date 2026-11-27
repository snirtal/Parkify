"""Active session reads. Entry and exit live on the gate controller."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.authorization import current_account, permission_required
from controllers.dependencies import current_services
from controllers.parsing import identifier
from controllers.presentation import omit_financial_fields
from controllers.serialization import dump
from services.permissions import PRICING_READ, SESSIONS_READ, allows

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/facilities/<facility_id>")


@sessions_bp.get("/sessions")
@permission_required(SESSIONS_READ)
def list_sessions(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    sessions = current_services().sessions.list_active_sessions(facility_id)
    return jsonify({"items": _visible(dump(sessions))}), 200


def _visible(payload: object) -> object:
    if allows(current_account().role, PRICING_READ):
        return payload
    return omit_financial_fields(payload)
