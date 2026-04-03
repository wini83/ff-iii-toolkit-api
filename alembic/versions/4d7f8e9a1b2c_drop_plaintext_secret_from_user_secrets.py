"""drop plaintext secret from user secrets

Revision ID: 4d7f8e9a1b2c
Revises: 8f4e1b6d2c3a
Create Date: 2026-04-03 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4d7f8e9a1b2c"
down_revision: Union[str, Sequence[str], None] = "8f4e1b6d2c3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_secrets", schema=None) as batch_op:
        batch_op.drop_column("secret")


def downgrade() -> None:
    with op.batch_alter_table("user_secrets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "secret",
                sa.Text(),
                nullable=False,
                server_default="",
            )
        )
