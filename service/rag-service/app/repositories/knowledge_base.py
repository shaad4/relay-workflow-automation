import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate


class KnowledgeBaseRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        workspace_id: uuid.UUID,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:

        knowledge_base = KnowledgeBase(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description,
        )

        self.db.add(knowledge_base)

        await self.db.flush()
        await self.db.refresh(knowledge_base)

        return knowledge_base
