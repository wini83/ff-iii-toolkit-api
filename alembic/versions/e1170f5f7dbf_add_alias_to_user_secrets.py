"""add alias to user secrets

Revision ID: e1170f5f7dbf
Revises: 5801f6f0a1a8
Create Date: 2026-03-14 21:07:51.148196

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1170f5f7dbf"
down_revision: Union[str, Sequence[str], None] = "5801f6f0a1a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("user_secrets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("alias", sa.String(length=16), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("user_secrets", schema=None) as batch_op:
        batch_op.drop_column("alias")
