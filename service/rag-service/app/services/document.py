import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document import DocumentRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository


class DocumentService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentRepository(db)
        self.knowledge_base_repository = KnowledgeBaseRepository(db)

    async def validate_knowledge_base(
        self,
        knowledge_base_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:

        knowledge_base = await self.knowledge_base_repository.get_by_id(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

        if knowledge_base is None:
            raise HTTPException(
                status_code=404,
                detail="Knowledge base not found",
            )