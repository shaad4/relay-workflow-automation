from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from datetime import datetime, timezone
from sqlalchemy import update


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

    
    async def resolve_event(
        self,
        event_id: UUID,
        workspace_id: UUID,
    ) -> DeadLetterEvent | None:
        """Atomically resolve a pending DLQ event."""


        result = await self.session.execute(
            update(DeadLetterEvent)
            .where(
                DeadLetterEvent.id == event_id,
                DeadLetterEvent.workspace_id == workspace_id,
                DeadLetterEvent.status == "pending",
            )
            .values(
                status="resolved",
                resolved_at=datetime.now(timezone.utc),
            )
            .returning(DeadLetterEvent)
        )

        return result.scalar_one_or_none()

    
    async def get_pending_for_replay(
        self,
        event_id: UUID,
        workspace_id: UUID,
    ) -> DeadLetterEvent | None:
        """Lock a pending DLQ event for safe replay."""

        result = await self.session.execute(
            select(DeadLetterEvent)
            .where(
                DeadLetterEvent.id == event_id,
                DeadLetterEvent.workspace_id == workspace_id,
                DeadLetterEvent.status == "pending",
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    
    async def mark_replayed(
        self,
        event: DeadLetterEvent,
    ) -> None:
        """Mark a locked DLQ event as replayed."""

        event.status = "replayed"
        event.resolved_at = datetime.now(timezone.utc)

        await self.session.flush()




    async def get_execution_workflows(self, workspace_id: UUID, execution_ids):
        """Load workflow snapshots for this page in one workspace-scoped query."""
        if not execution_ids:
            return {}
        result = await self.session.execute(
            select(Execution.id, Execution.workflow_id, Execution.workflow_name).where(
                Execution.workspace_id == workspace_id,
                Execution.id.in_(execution_ids),
            )
        )
        return {
            row.id: {"workflow_id": row.workflow_id, "workflow_name": row.workflow_name}
            for row in result
        }

    async def get_failed_node(self, workspace_id, execution_id, step_id):
        if step_id is None:
            return {}
        result = await self.session.execute(
            select(ExecutionStep.node_type, ExecutionStep.node_name)
            .join(Execution, Execution.id == ExecutionStep.execution_id)
            .where(Execution.workspace_id == workspace_id,
                   Execution.id == execution_id, ExecutionStep.id == step_id)
        )
        step = result.one_or_none()
        return {"failed_node_type": step.node_type, "failed_node_name": step.node_name} if step else {}

    async def has_downstream_action_attempts(
        self,
        execution_id: UUID,
        workspace_id: UUID,
        downstream_node_ids: set[str],
    ) -> bool:
        """
        Return True if any downstream external action
        has an execution-step record.

        Even a pending step is treated as an attempt
        to keep replay validation conservative.
        """

        if not downstream_node_ids:
            return False

        result = await self.session.execute(
            select(ExecutionStep.id)
            .join(
                Execution,
                Execution.id == ExecutionStep.execution_id,
            )
            .where(
                Execution.id == execution_id,
                Execution.workspace_id == workspace_id,
                ExecutionStep.node_id.in_(downstream_node_ids),
                ExecutionStep.node_type.in_(
                    (
                        "action.http_request",
                        "action.email",
                        "action.refund",
                    )
                ),
            )
            .limit(1)
        )

        return result.scalar_one_or_none() is not None

