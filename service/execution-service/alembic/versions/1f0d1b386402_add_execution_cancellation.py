
"""add execution cancellation

Revision ID: 1f0d1b386402
Revises: fd2300ee0233
Create Date: 2026-10-23 17:55:14.951663
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f0d1b386402"
down_revision: Union[str, Sequence[str], None] = "fd2300ee0233"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column(
            "cancel_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "executions",
        "cancel_requested_at",
    )
