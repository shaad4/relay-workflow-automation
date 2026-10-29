"""create oauth states table

Revision ID: 057ec9aecebf
Revises: 41544dc4c9b8
Create Date: 2026-10-03 11:13:11.938578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '057ec9aecebf'
down_revision: Union[str, Sequence[str], None] = '41544dc4c9b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'oauth_states',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('state', sa.String(length=255), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'expires_at',
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(
        op.f('ix_oauth_states_state'),
        'oauth_states',
        ['state'],
        unique=True,
    )

    op.create_index(
        op.f('ix_oauth_states_workspace_id'),
        'oauth_states',
        ['workspace_id'],
        unique=False,
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_oauth_states_workspace_id'),
        table_name='oauth_states',
    )

    op.drop_index(
        op.f('ix_oauth_states_state'),
        table_name='oauth_states',
    )

    op.drop_table('oauth_states')