from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dead_letter_event import DeadLetterEvent


class DeadLetterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_events(
        self,
        workspace_id: UUID,
        limit: int = 10,
        offset: int = 0,
        status: str | None = None,
    ):
        filters = [
            DeadLetterEvent.workspace_id == workspace_id
        ]

        if status is not None:
            filters.append(DeadLetterEvent.status == status)

        count_result = await self.session.execute(
            select(func.count(DeadLetterEvent.id))
            .where(*filters)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(DeadLetterEvent)
            .where(*filters)
            .order_by(
                DeadLetterEvent.created_at.desc(),
                DeadLetterEvent.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return result.scalars().all(), total

    
    async def get_by_id(
        self,
        event_id: UUID,
        workspace_id: UUID,
    ) -> DeadLetterEvent | None:
        """Get a DLQ event belonging to a workspace."""

        result = await self.session.execute(
            select(DeadLetterEvent).where(
                DeadLetterEvent.id == event_id,
                DeadLetterEvent.workspace_id == workspace_id,
            )
        )

        return result.scalar_one_or_none()

