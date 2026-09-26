import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workflow_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    node_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    node_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    position_x: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    position_y: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    configuration: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )