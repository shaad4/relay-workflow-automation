import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
    )

    error_message: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_documents_workspace_kb",
            "workspace_id",
            "knowledge_base_id",
        ),
        ForeignKeyConstraint(
            ["knowledge_base_id", "workspace_id"],
            ["knowledge_bases.id", "knowledge_bases.workspace_id"],
            ondelete="CASCADE",
            name="fk_documents_knowledge_base_workspace",
        ),
        UniqueConstraint(
            "id",
            "workspace_id",
            name="uq_documents_id_workspace",
        ),
    )
