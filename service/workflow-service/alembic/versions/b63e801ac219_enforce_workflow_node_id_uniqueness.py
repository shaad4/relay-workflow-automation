"""Enforce unique logical node IDs within workflow versions.

Revision ID: b63e801ac219
Revises: 093d41466667
Create Date: 2026-09-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b63e801ac219"
down_revision: Union[str, Sequence[str], None] = "093d41466667"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the earliest-created row (UUID breaks timestamp ties), which leaves
    # the logical node ID referenced by workflow_edges intact.
    op.execute(
        sa.text(
            """
            DELETE FROM workflow_nodes AS duplicate
            USING workflow_nodes AS keeper
            WHERE duplicate.workflow_version_id = keeper.workflow_version_id
              AND duplicate.node_id = keeper.node_id
              AND (duplicate.created_at, duplicate.id) > (keeper.created_at, keeper.id)
            """
        )
    )
    op.create_unique_constraint(
        "uq_workflow_nodes_version_node_id",
        "workflow_nodes",
        ["workflow_version_id", "node_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workflow_nodes_version_node_id",
        "workflow_nodes",
        type_="unique",
    )
