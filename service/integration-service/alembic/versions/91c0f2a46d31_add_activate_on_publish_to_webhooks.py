"""Track draft webhooks that should activate on publish."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91c0f2a46d31"
down_revision: Union[str, Sequence[str], None] = "f003c43fd071"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "webhooks",
        sa.Column("activate_on_publish", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("webhooks", "activate_on_publish")
