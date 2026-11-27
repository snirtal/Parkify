"""Reservation endpoints. Cancellation keeps the row and marks it Cancelled."""

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
    query_text,
    query_timestamp,
    required_text,
    required_timestamp,
)
from controllers.serialization import dump
from services.permissions import RESERVATIONS_MANAGE, RESERVATIONS_READ
from utils.errors import AppError

RESERVATION_STATUSES = ("Active", "Scheduled", "Completed", "Cancelled")

reservations_bp = Blueprint(
    "reservations",
    __name__,
    url_prefix="/api/facilities/<facility_id>",
)


@reservations_bp.get("/reservations")
@permission_required(RESERVATIONS_READ)
def list_reservations(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    status = query_choice("status", RESERVATION_STATUSES)
    spot_code = query_text("spot_code", maximum=16)
    plate_number = query_text("plate_number", maximum=16)
    range_start = query_timestamp("range_start", required=False)
    range_end = query_timestamp("range_end", required=False)
    reservations = current_services().reservations.list_reservations(
        facility_id,
        status=status,
        spot_code=spot_code,
        plate_number=plate_number,
        range_start=range_start,
        range_end=range_end,
    )
    return jsonify({"items": dump(reservations)}), 200


@reservations_bp.post("/reservations")
@permission_required(RESERVATIONS_MANAGE)
def create_reservation(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    payload = json_object()
    plate_number = required_text(payload, "plate_number", maximum=16)
    spot_code = required_text(payload, "spot_code", maximum=16)
    starts_at = required_timestamp(payload, "starts_at")
    ends_at = required_timestamp(payload, "ends_at")
    driver_name = optional_text(payload, "driver_name", maximum=80)
    created = current_services().reservations.create_reservation(
        facility_id,
        plate_number,
        spot_code,
        starts_at,
        ends_at,
        driver_name=driver_name,
    )
    return jsonify(dump(created)), 201


@reservations_bp.post("/reservations/lifecycle")
@permission_required(RESERVATIONS_MANAGE)
def refresh_reservation_lifecycle(facility_id: str):
    facility_id = identifier(facility_id, "facility_id")
    refreshed = current_services().reservations.refresh_lifecycle(facility_id)
    return jsonify({"items": dump(refreshed)}), 200


@reservations_bp.get("/reservations/<reservation_id>")
@permission_required(RESERVATIONS_READ)
def get_reservation(facility_id: str, reservation_id: str):
    facility_id = identifier(facility_id, "facility_id")
    reservation_id = identifier(reservation_id, "reservation_id")
    reservation = current_services().reservations.get_reservation(facility_id, reservation_id)
    return jsonify(dump(reservation)), 200


@reservations_bp.patch("/reservations/<reservation_id>")
@permission_required(RESERVATIONS_MANAGE)
def update_reservation(facility_id: str, reservation_id: str):
    facility_id = identifier(facility_id, "facility_id")
    reservation_id = identifier(reservation_id, "reservation_id")
    payload = json_object()
    if not any(
        name in payload
        for name in ("plate_number", "spot_code", "starts_at", "ends_at", "driver_name")
    ):
        raise AppError(
            "Provide at least one reservation field to update.",
            code="validation_error",
            status_code=400,
        )
    plate_number = optional_text(payload, "plate_number", maximum=16)
    spot_code = optional_text(payload, "spot_code", maximum=16)
    starts_at = optional_timestamp(payload, "starts_at")
    ends_at = optional_timestamp(payload, "ends_at")
    driver_name = optional_text(payload, "driver_name", maximum=80)
    updated = current_services().reservations.update_reservation(
        facility_id,
        reservation_id,
        plate_number=plate_number,
        spot_code=spot_code,
        starts_at=starts_at,
        ends_at=ends_at,
        driver_name=driver_name,
    )
    return jsonify(dump(updated)), 200


@reservations_bp.post("/reservations/<reservation_id>/cancellation")
@permission_required(RESERVATIONS_MANAGE)
def cancel_reservation(facility_id: str, reservation_id: str):
    facility_id = identifier(facility_id, "facility_id")
    reservation_id = identifier(reservation_id, "reservation_id")
    cancelled = current_services().reservations.cancel_reservation(facility_id, reservation_id)
    return jsonify(dump(cancelled)), 200
