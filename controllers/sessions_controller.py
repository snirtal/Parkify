"""Active session reads. Entry and exit live on the gate controller."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.authorization import permission_required
from controllers.dependencies import current_services
from controllers.parsing import identifier
from controllers.serialization import dump
from services.permissions import SESSIONS_READ

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/facilities/<facility_id>")


@sessions_bp.get("/sessions")
@permission_required(SESSIONS_READ)
def list_sessions(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    sessions = current_services().sessions.list_active_sessions(facility_id)
    return jsonify({"items": dump(sessions)}), 200
