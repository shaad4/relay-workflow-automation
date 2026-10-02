"""rename credential ref to credential

Revision ID: 41544dc4c9b8
Revises: ebdf53b85ccc
Create Date: 2026-10-02 16:46:43.374796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '41544dc4c9b8'
down_revision: Union[str, Sequence[str], None] = 'ebdf53b85ccc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "connections",
        "credential_ref",
        new_column_name="credential",
    )


def downgrade() -> None:
    op.alter_column(
        "connections",
        "credential",
        new_column_name="credential_ref",
    )