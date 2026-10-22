from uuid import UUID

from app.repositories.dead_letter import DeadLetterRepository


class DeadLetterService:
    def __init__(self, repository: DeadLetterRepository):
        self.repository = repository

    async def list_events(
        self,
        workspace_id: UUID,
        limit: int = 10,
        offset: int = 0,
        status: str | None = None,
    ) -> dict:
        """List dead-letter events for one workspace."""

        events, total = await self.repository.list_events(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            status=status,
        )

        return {
            "items": [
                {
                    "id": event.id,
                    "execution_id": event.execution_id,
                    "execution_step_id": event.execution_step_id,
                    "event_type": event.event_type,
                    "attempts": event.attempts,
                    "status": event.status,
                    "error": event.error,
                    "created_at": event.created_at,
                    "resolved_at": event.resolved_at,
                }
                for event in events
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
