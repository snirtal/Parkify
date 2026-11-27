"""Facility settings. Omitted fields keep their stored values."""

from __future__ import annotations

from flask import Blueprint, jsonify

from controllers.authorization import permission_required
from controllers.dependencies import current_services
from controllers.parsing import (
    identifier,
    json_object,
    optional_bool,
    optional_money,
    optional_text,
    optional_whole_number,
)
from controllers.serialization import dump
from services.permissions import SETTINGS_MANAGE, SETTINGS_READ
from services.results import FacilitySettingsUpdate
from utils.errors import AppError

settings_bp = Blueprint("settings", __name__, url_prefix="/api/facilities/<facility_id>")

_FIELDS = (
    "facility_name",
    "facility_address",
    "operating_hours",
    "hourly_rate",
    "daily_max_rate",
    "grace_period_minutes",
    "ev_surcharge",
    "high_occupancy_alert",
    "reservation_overstay_alert",
    "space_fault_alert",
)


@settings_bp.get("/settings")
@permission_required(SETTINGS_READ)
def get_settings(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    settings = current_services().settings.get_settings(facility_id)
    return jsonify(dump(settings)), 200


@settings_bp.patch("/settings")
@permission_required(SETTINGS_MANAGE)
def update_settings(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    payload = json_object()
    if not any(name in payload for name in _FIELDS):
        raise AppError(
            "Provide at least one settings field to update.",
            code="validation_error",
            status_code=400,
        )
    changes = FacilitySettingsUpdate(
        facility_name=optional_text(payload, "facility_name", maximum=120),
        facility_address=optional_text(payload, "facility_address", maximum=180),
        operating_hours=optional_text(payload, "operating_hours", maximum=80),
        hourly_rate=optional_money(payload, "hourly_rate"),
        daily_max_rate=optional_money(payload, "daily_max_rate"),
        grace_period_minutes=optional_whole_number(payload, "grace_period_minutes"),
        ev_surcharge=optional_money(payload, "ev_surcharge"),
        high_occupancy_alert=optional_bool(payload, "high_occupancy_alert"),
        reservation_overstay_alert=optional_bool(payload, "reservation_overstay_alert"),
        space_fault_alert=optional_bool(payload, "space_fault_alert"),
    )
    updated = current_services().settings.update_settings(facility_id, changes)
    return jsonify(dump(updated)), 200
