from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution
from app.models.idempotency_key import IdempotencyKey
from app.engine.status import ExecutionStatus


class ExecutionQueueRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_event_key(
        self,
        workspace_id: UUID,
        key: str,
    ) -> Execution | None:
        statement = (
            select(Execution)
            .join(
                IdempotencyKey,
                IdempotencyKey.execution_id == Execution.id,
            )
            .where(
                IdempotencyKey.workspace_id == workspace_id,
                IdempotencyKey.key == key,
                Execution.workspace_id == workspace_id,
            )
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def create_pending(
        self,
        *,
        workspace_id: UUID,
        workflow_id: UUID,
        workflow_version_id: UUID,
        trigger_type: str,
        trigger_data: dict,
        event_key: str,
    ) -> Execution:
        execution = Execution(
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            workflow_version_id=workflow_version_id,
            status=ExecutionStatus.PENDING,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            context={},
        )

        self.session.add(execution)

        await self.session.flush()

        idempotency_key = IdempotencyKey(
            workspace_id=workspace_id,
            key=event_key,
            execution_id=execution.id,
        )

        self.session.add(idempotency_key)

        await self.session.flush()

        return execution
