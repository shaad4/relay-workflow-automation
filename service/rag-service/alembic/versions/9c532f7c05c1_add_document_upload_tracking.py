
"""add document upload tracking

Revision ID: 9c532f7c05c1
Revises: a341a4d42994
Create Date: 2026-10-11 19:16:16.387698
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision: str = "9c532f7c05c1"
down_revision: Union[str, Sequence[str], None] = "a341a4d42994"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add document upload tracking timestamp."""

    op.add_column(
        "documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove document upload tracking timestamp."""

    op.drop_column(
        "documents",
        "updated_at",
    )
