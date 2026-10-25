from uuid import UUID

from sqlalchemy import select, update, func, text
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


    async def claim_pending(
        self,
        execution_id: UUID,
        worker_id: str,
        lease_seconds: int = 120,
    ) -> bool:
        """
        Atomically claim a pending execution.

        Only one worker can change its status
        from pending to running.
        """

        if not worker_id or len(worker_id) > 100:
            raise ValueError("Invalid worker ID")

        if lease_seconds < 1:
            raise ValueError(
                "lease_seconds must be positive"
            )

        statement = (
            update(Execution)
            .where(
                Execution.id == execution_id,
                Execution.status == ExecutionStatus.PENDING,
            )
            .values(
                status=ExecutionStatus.RUNNING,
                claimed_by=worker_id,
                started_at=func.coalesce(
                    Execution.started_at,
                    func.now(),
                ),
                heartbeat_at=func.now(),
                lease_expires_at=(
                    func.now()
                    + text(
                        f"INTERVAL '{lease_seconds} seconds'"
                    )
                ),
            )
            .returning(Execution.id)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none() is not None


    
    async def renew_lease(
        self,
        execution_id: UUID,
        worker_id: str,
        lease_seconds: int = 120,
    ) -> bool:
        """
        Renew the lease only if this worker
        still owns the running execution.
        """

        if not worker_id or len(worker_id) > 100:
            raise ValueError("Invalid worker ID")

        if not 1 <= lease_seconds <= 3600:
            raise ValueError("Invalid lease duration")

        statement = (
            update(Execution)
            .where(
                Execution.id == execution_id,
                Execution.status == ExecutionStatus.RUNNING,
                Execution.claimed_by == worker_id,
                Execution.lease_expires_at > func.now(),
            )
            .values(
                heartbeat_at=func.now(),
                lease_expires_at=(
                    func.now()
                    + func.make_interval(
                        0, 0, 0, 0, 0, 0, lease_seconds
                    )
                ),
            )
            .returning(Execution.id)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none() is not None


    async def list_expired_executions(
        self,
        limit: int = 100,
    ) -> list[Execution]:
        """Find running executions whose worker leases expired."""

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        statement = (
            select(Execution)
            .where(
                Execution.status == ExecutionStatus.RUNNING,
                Execution.lease_expires_at.is_not(None),
                Execution.lease_expires_at <= func.now(),
            )
            .order_by(Execution.lease_expires_at)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    
    async def mark_expired_as_failed(
        self,
        execution_id: UUID,
        workspace_id: UUID,
    ) -> bool:
        """
        Atomically mark an expired running execution as failed.

        Does not restart or replay the workflow.
        """

        statement = (
            update(Execution)
            .where(
                Execution.id == execution_id,
                Execution.workspace_id == workspace_id,
                Execution.status == ExecutionStatus.RUNNING,
                Execution.lease_expires_at.is_not(None),
                Execution.lease_expires_at <= func.now(),
            )
            .values(
                status=ExecutionStatus.FAILED,
                claimed_by=None,
                heartbeat_at=None,
                lease_expires_at=None,
                completed_at=func.now(),
                error={
                    "error_code": "WORKER_INTERRUPTED",
                    "message": (
                        "Execution stopped because the "
                        "worker lease expired"
                    ),
                    "retryable": False,
                    "requires_review": True,
                },
            )
            .returning(Execution.id)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none() is not None



    async def list_pending_executions(
        self,
        limit: int = 100,
    ) -> list[Execution]:
        """Find executions that have not yet been claimed."""

        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        statement = (
            select(Execution)
            .where(
                Execution.status == ExecutionStatus.PENDING,
            )
            .order_by(Execution.created_at)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

