
import uuid

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        filename: str,
        content_type: str,
        file_size: int,
        storage_path: str,
        status: str = "uploading",
    ) -> Document:

        document = Document(
            id=document_id,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
            status=status,
        )

        self.db.add(document)

        await self.db.flush()
        await self.db.refresh(document)

        return document


    async def update_status(
        self,
        document: Document,
        status: str,
        error_message: str | None = None,
    ) -> Document:
        document.status = status
        document.error_message = error_message

        await self.db.flush()
        return document

    async def get_by_id(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> Document | None:
        """Retrieve a document belonging to a workspace."""

        statement = (
            select(Document)
            .where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
            )
        )

        result = await self.db.execute(statement)

        return result.scalar_one_or_none()

    async def claim_for_ingestion(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        """Atomically claim a pending document for ingestion."""

        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
                Document.status == "pending",
            )
            .values(status="parsing")
            .returning(Document.id)
        )

        result = await self.db.execute(statement)

        return result.scalar_one_or_none() is not None


    async def list_by_knowledge_base(
        self,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> list[Document]:
        """List documents belonging to a workspace's knowledge base."""

        statement = (
            select(Document)
            .where(
                Document.workspace_id == workspace_id,
                Document.knowledge_base_id == knowledge_base_id,
            )
            .order_by(Document.created_at.desc())
        )

        result = await self.db.execute(statement)

        return list(result.scalars().all())

    async def delete(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> bool:
        """Delete a document belonging to a workspace and knowledge base."""

        statement = (
            select(Document)
            .where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
                Document.knowledge_base_id == knowledge_base_id,
            )
        )

        result = await self.db.execute(statement)
        document = result.scalar_one_or_none()

        if document is None:
            return False

        await self.db.delete(document)
        await self.db.flush()

        return True
