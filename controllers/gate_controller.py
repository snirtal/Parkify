"""Gate entry, exit, and activity.

Entry and exit call the gate service so the session change and the gate
event commit or roll back together.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.authorization import permission_required
from controllers.dependencies import current_services
from controllers.parsing import (
    identifier,
    json_object,
    optional_text,
    optional_timestamp,
    query_choice,
    query_int,
    query_text,
    query_timestamp,
    required_text,
)
from controllers.serialization import dump
from services.permissions import GATE_OPERATE, GATE_READ
from utils.errors import AppError

gate_bp = Blueprint("gate", __name__, url_prefix="/api/facilities/<facility_id>")


@gate_bp.post("/entries")
@permission_required(GATE_OPERATE)
def record_entry(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    payload = json_object()
    plate_number = required_text(payload, "plate_number", maximum=16)
    spot_code = required_text(payload, "spot_code", maximum=16)
    gate_name = optional_text(payload, "gate_name", maximum=80)
    driver_name = optional_text(payload, "driver_name", maximum=80)
    at = optional_timestamp(payload, "at")
    change = current_services().gate.record_entry(
        facility_id,
        plate_number,
        spot_code,
        gate_name=gate_name,
        driver_name=driver_name,
        at=at,
    )
    return jsonify(dump(change)), 201


@gate_bp.post("/exits")
@permission_required(GATE_OPERATE)
def record_exit(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    payload = json_object()
    plate_number = optional_text(payload, "plate_number", maximum=16)
    session_id = optional_text(payload, "session_id", maximum=64)
    gate_name = optional_text(payload, "gate_name", maximum=80)
    at = optional_timestamp(payload, "at")
    if plate_number is None and session_id is None:
        raise AppError(
            "plate_number or session_id is required.",
            code="validation_error",
            status_code=400,
        )
    change = current_services().gate.record_exit(
        facility_id,
        plate_number=plate_number,
        session_id=session_id,
        gate_name=gate_name,
        at=at,
    )
    return jsonify(dump(change)), 200


@gate_bp.get("/gate-activity")
@permission_required(GATE_READ)
def list_gate_activity(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    spot_code = query_text("spot_code", maximum=16)
    plate_number = query_text("plate_number", maximum=16)
    direction = query_choice("direction", ("entry", "exit"))
    status = query_choice("status", ("Active", "Completed", "Reserved"))
    occurred_from = query_timestamp("occurred_from", required=False)
    occurred_to = query_timestamp("occurred_to", required=False)
    limit = query_int("limit", default=20, minimum=1, maximum=100)
    offset = query_int("offset", default=0, minimum=0, maximum=100_000)
    page = current_services().gate.list_activity(
        facility_id,
        spot_code=spot_code,
        plate_number=plate_number,
        direction=direction,
        status=status,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
        offset=offset,
    )
    return jsonify(dump(page)), 200
