
import uuid

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
    ) -> Document:

        document = Document(
            id=document_id,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            storage_path=storage_path,
            status="pending",
        )

        self.db.add(document)

        await self.db.flush()
        await self.db.refresh(document)

        return document
