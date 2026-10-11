import uuid

from sqlalchemy import select
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


    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
    ) -> list[KnowledgeBase]:

        statement = (
            select(KnowledgeBase)
            .where(KnowledgeBase.workspace_id == workspace_id)
            .order_by(KnowledgeBase.created_at.desc())
        )

        result = await self.db.execute(statement)

        return list(result.scalars().all())


    async def get_by_id(
        self,
        knowledge_base_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> KnowledgeBase | None:

        statement = (
            select(KnowledgeBase)
            .where(
                KnowledgeBase.id == knowledge_base_id,
                KnowledgeBase.workspace_id == workspace_id,
            )
        )

        result = await self.db.execute(statement)

        return result.scalar_one_or_none()
