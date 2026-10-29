"""rename webhook secret ref to hash

Revision ID: f003c43fd071
Revises: 5106f1b1289d
Create Date: 2026-09-30 22:16:31.197942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f003c43fd071'
down_revision: Union[str, Sequence[str], None] = '5106f1b1289d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "webhooks",
        "secret_ref",
        new_column_name="secret_hash",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "webhooks",
        "secret_hash",
        new_column_name="secret_ref",
    )