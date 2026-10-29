
"""add execution metadata snapshots

Revision ID: 1dfee2bc84aa
Revises: e631cbdeb8f9
Create Date: 2026-10-19 15:20:50.397718
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1dfee2bc84aa"
down_revision: Union[str, Sequence[str], None] = "e631cbdeb8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column(
            "workflow_name",
            sa.String(length=200),
            nullable=True,
        ),
    )

    op.add_column(
        "execution_steps",
        sa.Column(
            "node_name",
            sa.String(length=200),
            nullable=True,
        ),
    )

    op.add_column(
        "execution_steps",
        sa.Column(
            "node_type",
            sa.String(length=100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "execution_steps",
        "node_type",
    )

    op.drop_column(
        "execution_steps",
        "node_name",
    )

    op.drop_column(
        "executions",
        "workflow_name",
    )
