"""add user secret crypto fields and vaults

Revision ID: 8f4e1b6d2c3a
Revises: e1170f5f7dbf
Create Date: 2026-03-30 00:00:00.000000

"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import CHAR
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(str(value))


# revision identifiers, used by Alembic.
revision: str = "8f4e1b6d2c3a"
down_revision: Union[str, Sequence[str], None] = "e1170f5f7dbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_secrets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("external_username", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("ciphertext", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("secret_nonce", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("wrapped_dek", sa.LargeBinary(), nullable=True))
        batch_op.add_column(
            sa.Column("wrapped_dek_nonce", sa.LargeBinary(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "crypto_version",
                sa.Integer(),
                nullable=True,
            )
        )

    op.create_table(
        "user_secret_vaults",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("kdf_salt", sa.LargeBinary(), nullable=True),
        sa.Column("kdf_params_json", sa.JSON(), nullable=True),
        sa.Column("vault_check_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("vault_check_nonce", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_secret_vaults")

    with op.batch_alter_table("user_secrets", schema=None) as batch_op:
        batch_op.drop_column("crypto_version")
        batch_op.drop_column("wrapped_dek_nonce")
        batch_op.drop_column("wrapped_dek")
        batch_op.drop_column("secret_nonce")
        batch_op.drop_column("ciphertext")
        batch_op.drop_column("external_username")
