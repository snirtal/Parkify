"""Initial Parkify schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-25

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "facilities",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("address", sa.String(length=180), nullable=False),
        sa.Column("operating_hours", sa.String(length=80), nullable=False),
        sa.Column("simulated_date", sa.Date(), nullable=False),
        sa.Column("simulated_time", sa.Time(), nullable=False),
        sa.Column("snapshot_label", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "facility_settings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(8, 2), nullable=False),
        sa.Column("daily_max_rate", sa.Numeric(8, 2), nullable=False),
        sa.Column("grace_period_minutes", sa.Integer(), nullable=False),
        sa.Column("ev_surcharge", sa.Numeric(8, 2), nullable=False),
        sa.Column("high_occupancy_alert", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "reservation_overstay_alert",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("space_fault_alert", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("facility_id"),
        sa.CheckConstraint("hourly_rate > 0", name="ck_facility_settings_hourly_rate"),
        sa.CheckConstraint("daily_max_rate > 0", name="ck_facility_settings_daily_max"),
        sa.CheckConstraint(
            "daily_max_rate >= hourly_rate",
            name="ck_facility_settings_daily_covers_hourly",
        ),
        sa.CheckConstraint(
            "grace_period_minutes >= 0 AND grace_period_minutes <= 180",
            name="ck_facility_settings_grace_period",
        ),
        sa.CheckConstraint("ev_surcharge >= 0", name="ck_facility_settings_ev_surcharge"),
    )

    op.create_table(
        "floors",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("level_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("facility_id", "code", name="uq_floors_facility_code"),
        sa.UniqueConstraint("facility_id", "level_index", name="uq_floors_facility_level"),
    )

    op.create_table(
        "parking_zones",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("floor_id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("dashboard_category", sa.String(length=32), nullable=False),
        sa.Column("accent", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("floor_id", "code", name="uq_parking_zones_floor_code"),
    )

    op.create_table(
        "parking_spots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("floor_id", sa.String(length=64), nullable=False),
        sa.Column("zone_id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("row", sa.String(length=16), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("bay_class", sa.String(length=32), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(8, 2), nullable=False),
        sa.Column("sensor_note", sa.Text(), nullable=False),
        sa.Column("maintenance_reason", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"]),
        sa.ForeignKeyConstraint(["zone_id"], ["parking_zones.id"]),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint(
            "floor_id", "row", "slot_index", name="uq_parking_spots_floor_row_slot"
        ),
        sa.CheckConstraint("row IN ('north', 'south')", name="ck_parking_spots_row"),
        sa.CheckConstraint(
            "bay_class IN ('Standard', 'EV Fast 150kW', 'VIP Priority', 'Accessible')",
            name="ck_parking_spots_bay_class",
        ),
        sa.CheckConstraint("hourly_rate > 0", name="ck_parking_spots_hourly_rate"),
    )
    op.create_index("ix_parking_spots_zone_id", "parking_spots", ["zone_id"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("plate_number", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=80)),
        sa.Column("body_type", sa.String(length=32)),
        sa.Column("color_hex", sa.String(length=16)),
        sa.Column("accent_hex", sa.String(length=16)),
        sa.Column("driver_name", sa.String(length=80)),
        sa.Column("driver_initials", sa.String(length=8)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("plate_number"),
    )

    op.create_table(
        "parking_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("spot_id", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime()),
        sa.Column("paid_until", sa.DateTime()),
        sa.Column("until_caption", sa.String(length=80)),
        sa.Column("monitoring_label", sa.String(length=80)),
        sa.Column("has_alert", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("alert_title", sa.String(length=80)),
        sa.Column("alert_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["spot_id"], ["parking_spots.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.CheckConstraint(
            "status IN ('Active', 'Completed')",
            name="ck_parking_sessions_status",
        ),
        sa.CheckConstraint(
            "(status = 'Active' AND ended_at IS NULL) OR "
            "(status = 'Completed' AND ended_at IS NOT NULL AND ended_at >= started_at)",
            name="ck_parking_sessions_lifecycle",
        ),
    )
    op.create_index("ix_parking_sessions_vehicle_id", "parking_sessions", ["vehicle_id"])
    op.create_index("ix_parking_sessions_spot_id", "parking_sessions", ["spot_id"])
    op.create_index(
        "uq_parking_sessions_open_spot",
        "parking_sessions",
        ["spot_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )

    op.create_table(
        "reservations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("spot_id", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("is_seeded", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["spot_id"], ["parking_spots.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.CheckConstraint(
            "status IN ('Active', 'Scheduled', 'Completed', 'Cancelled')",
            name="ck_reservations_status",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_reservations_window"),
    )
    op.create_index("ix_reservations_spot_starts", "reservations", ["spot_id", "starts_at"])
    op.create_index("ix_reservations_vehicle_id", "reservations", ["vehicle_id"])
    op.execute(
        """
        ALTER TABLE reservations
        ADD CONSTRAINT ex_reservations_no_overlap
        EXCLUDE USING gist (
            spot_id WITH =,
            tsrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status <> 'Cancelled')
        """
    )

    op.create_table(
        "gate_activities",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("spot_id", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=64), nullable=False),
        sa.Column("reservation_id", sa.String(length=64)),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("gate_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("duration_label", sa.String(length=32)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["spot_id"], ["parking_spots.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
        sa.CheckConstraint(
            "direction IN ('entry', 'exit')",
            name="ck_gate_activities_direction",
        ),
        sa.CheckConstraint(
            "status IN ('Active', 'Completed', 'Reserved')",
            name="ck_gate_activities_status",
        ),
    )
    op.create_index("ix_gate_activities_occurred_at", "gate_activities", ["occurred_at"])
    op.create_index("ix_gate_activities_spot_id", "gate_activities", ["spot_id"])


def downgrade() -> None:
    op.drop_table("gate_activities")
    op.drop_table("reservations")
    op.drop_table("parking_sessions")
    op.drop_table("vehicles")
    op.drop_table("parking_spots")
    op.drop_table("parking_zones")
    op.drop_table("floors")
    op.drop_table("facility_settings")
    op.drop_table("facilities")
