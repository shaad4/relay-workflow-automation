from uuid import UUID

from app.repositories.execution import ExecutionRepository


class ExecutionCancellationService:
    def __init__(self, repository: ExecutionRepository):
        self.repository = repository

    async def cancel_execution(
        self,
        execution_id: UUID,
        workspace_id: UUID,
    ) -> str | None:
        try:
            status = await self.repository.request_cancellation(
                execution_id=execution_id,
                workspace_id=workspace_id,
            )

            if status in {
                "cancelled",
                "cancellation_requested",
            }:
                await self.repository.session.commit()
            else:
                await self.repository.session.rollback()

            return status

        except Exception:
            await self.repository.session.rollback()
            raise
