import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.knowledge_base import KnowledgeBaseCreate


class KnowledgeBaseService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = KnowledgeBaseRepository(db)

    async def create(
        self,
        workspace_id: uuid.UUID,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:

        try:
            knowledge_base = await self.repository.create(
                workspace_id=workspace_id,
                data=data,
            )

            await self.db.commit()

            return knowledge_base

        except Exception:
            await self.db.rollback()
            raise
