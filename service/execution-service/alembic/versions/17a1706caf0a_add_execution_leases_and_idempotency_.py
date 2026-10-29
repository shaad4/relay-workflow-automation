
"""add execution leases and idempotency keys

Revision ID: 17a1706caf0a
Revises: 1dfee2bc84aa
Create Date: 2026-10-20 14:24:12.609072
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Alembic revision identifiers.
revision: str = "17a1706caf0a"
down_revision: Union[str, Sequence[str], None] = (
    "1dfee2bc84aa"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add execution worker leases and idempotency keys."""

    # 1. Worker ownership and heartbeat fields.
    op.add_column(
        "executions",
        sa.Column(
            "claimed_by",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "executions",
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "executions",
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # 2. Create idempotency_keys table.
    op.create_table(
        "idempotency_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "key",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "execution_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["executions.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "key",
            name="uq_idempotency_workspace_key",
        ),
    )

    # 3. Indexes for workspace and execution lookups.
    op.create_index(
        "ix_idempotency_keys_workspace_id",
        "idempotency_keys",
        ["workspace_id"],
    )

    op.create_index(
        "ix_idempotency_keys_execution_id",
        "idempotency_keys",
        ["execution_id"],
    )


def downgrade() -> None:
    """Remove idempotency keys and execution lease fields."""

    op.drop_index(
        "ix_idempotency_keys_execution_id",
        table_name="idempotency_keys",
    )

    op.drop_index(
        "ix_idempotency_keys_workspace_id",
        table_name="idempotency_keys",
    )

    op.drop_table("idempotency_keys")

    op.drop_column(
        "executions",
        "lease_expires_at",
    )

    op.drop_column(
        "executions",
        "heartbeat_at",
    )

    op.drop_column(
        "executions",
        "claimed_by",
    )
