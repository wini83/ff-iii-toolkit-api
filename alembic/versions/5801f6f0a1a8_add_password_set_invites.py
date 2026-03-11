"""add password set invites

Revision ID: 5801f6f0a1a8
Revises: adc7ba2730be
Create Date: 2026-03-11 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.services.db.types import GUID


# revision identifiers, used by Alembic.
revision: str = "5801f6f0a1a8"
down_revision: Union[str, Sequence[str], None] = "adc7ba2730be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.create_table(
        "user_password_set_tokens",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", GUID(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_user_password_set_tokens_user_id",
        "user_password_set_tokens",
        ["user_id"],
        unique=False,
    )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("must_change_password", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_user_password_set_tokens_user_id",
        table_name="user_password_set_tokens",
    )
    op.drop_table("user_password_set_tokens")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("must_change_password")
