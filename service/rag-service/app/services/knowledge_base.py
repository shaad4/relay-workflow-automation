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

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
    ) -> list[KnowledgeBase]:

        return await self.repository.list_by_workspace(
            workspace_id=workspace_id,
        )

    async def get_by_id(
        self,
        knowledge_base_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> KnowledgeBase | None:

        return await self.repository.get_by_id(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

    async def delete(
        self,
        knowledge_base_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> bool:
        try:
            deleted = await self.repository.delete(
                knowledge_base_id=knowledge_base_id,
                workspace_id=workspace_id,
            )

            if not deleted:
                return False

            await self.db.commit()
            return True

        except Exception:
            await self.db.rollback()
            raise
