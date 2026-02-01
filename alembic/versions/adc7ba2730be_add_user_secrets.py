"""add user secrets

Revision ID: adc7ba2730be
Revises: 287bec6d8d4e
Create Date: 2026-02-01 15:58:39.472847

"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from src.services.db.types import GUID  # ważne: używamy Twojego GUID()

# revision identifiers, used by Alembic.
revision: str = 'adc7ba2730be'
down_revision: Union[str, Sequence[str], None] = '287bec6d8d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_secrets",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("secret", sa.Text(), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_secrets_user_id_users",
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_user_secrets_user_id",
        "user_secrets",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_secrets_type",
        "user_secrets",
        ["type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_secrets_type", table_name="user_secrets")
    op.drop_index("ix_user_secrets_user_id", table_name="user_secrets")
    op.drop_table("user_secrets")
