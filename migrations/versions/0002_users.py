"""Operator accounts.

Revision ID: 0002_users
Revises: 0001_initial_schema
Create Date: 2026-11-27

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_users"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('admin', 'employee')", name="ck_users_role"),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_normalized"),
        sa.CheckConstraint("char_length(full_name) >= 2", name="ck_users_full_name"),
        sa.CheckConstraint("char_length(password_hash) >= 20", name="ck_users_password_hash"),
    )


def downgrade() -> None:
    op.drop_table("users")
