
"""add tenant isolation constraints

Revision ID: c90268304be4
Revises: 93fea55b442b
Create Date: 2026-10-11 08:50:52.544203
"""

from typing import Sequence, Union

from alembic import op


# Revision identifiers
revision: str = "c90268304be4"
down_revision: Union[str, Sequence[str], None] = "93fea55b442b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add workspace-level tenant isolation constraints."""

    # 1. Parent unique constraint
    op.create_unique_constraint(
        "uq_knowledge_bases_id_workspace",
        "knowledge_bases",
        ["id", "workspace_id"],
    )

    # 2. Document unique constraint
    op.create_unique_constraint(
        "uq_documents_id_workspace",
        "documents",
        ["id", "workspace_id"],
    )

    # 3. Remove existing single-column foreign key
    op.drop_constraint(
        "documents_knowledge_base_id_fkey",
        "documents",
        type_="foreignkey",
    )

    # 4. Create tenant-aware composite foreign key
    op.create_foreign_key(
        "fk_documents_knowledge_base_workspace",
        "documents",
        "knowledge_bases",
        ["knowledge_base_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Remove workspace-level tenant isolation constraints."""

    # 1. Remove composite foreign key
    op.drop_constraint(
        "fk_documents_knowledge_base_workspace",
        "documents",
        type_="foreignkey",
    )

    # 2. Restore original foreign key
    op.create_foreign_key(
        "documents_knowledge_base_id_fkey",
        "documents",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. Remove document unique constraint
    op.drop_constraint(
        "uq_documents_id_workspace",
        "documents",
        type_="unique",
    )

    # 4. Remove knowledge base unique constraint
    op.drop_constraint(
        "uq_knowledge_bases_id_workspace",
        "knowledge_bases",
        type_="unique",
    )
