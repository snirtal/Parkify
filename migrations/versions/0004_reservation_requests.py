"""Reservation requests and the simulator role.

Revision ID: 0004_reservation_requests
Revises: 0003_auth_sessions
Create Date: 2026-11-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_reservation_requests"
down_revision: str | None = "0003_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'employee', 'simulator')",
    )
    op.create_table(
        "reservation_requests",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=64), nullable=False),
        sa.Column("bay_class", sa.String(length=32), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reservation_id", sa.String(length=64), nullable=True),
        sa.Column("decided_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('Pending', 'Approved', 'Rejected', 'Expired')",
            name="ck_reservation_requests_status",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_reservation_requests_window"),
        sa.CheckConstraint(
            "bay_class IN ('Standard', 'EV Fast 150kW', 'VIP Priority', 'Accessible')",
            name="ck_reservation_requests_bay_class",
        ),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_reservation_requests_facility_status",
        "reservation_requests",
        ["facility_id", "status"],
    )
    op.create_index(
        "uq_reservation_requests_pending_vehicle",
        "reservation_requests",
        ["facility_id", "vehicle_id"],
        unique=True,
        postgresql_where=sa.text("status = 'Pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_reservation_requests_pending_vehicle", table_name="reservation_requests")
    op.drop_index("ix_reservation_requests_facility_status", table_name="reservation_requests")
    op.drop_table("reservation_requests")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'employee')",
    )
