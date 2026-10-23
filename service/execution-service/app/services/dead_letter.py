import json

from uuid import UUID, uuid4
from sqlalchemy import select

from app.repositories.dead_letter import DeadLetterRepository
from app.engine.graph import ExecutionGraph
from app.engine.status import ExecutionStatus
from app.grpc.workflow_client import WorkflowClient
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.services.replay_validator import validate_replay_path

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

        workflows = await self.repository.get_execution_workflows(
            workspace_id, [event.execution_id for event in events],
        )
        return {
            "items": [
                {
                    "id": event.id,
                    "execution_id": event.execution_id,
                    **workflows.get(event.execution_id, {}),
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

    
    async def get_event(
        self,
        event_id: UUID,
        workspace_id: UUID,
    ) -> dict | None:
        """Return one dead-letter event."""

        event = await self.repository.get_by_id(
            event_id=event_id,
            workspace_id=workspace_id,
        )

        if event is None:
            return None

        workflows = await self.repository.get_execution_workflows(
            workspace_id, [event.execution_id],
        )
        failed_node = await self.repository.get_failed_node(
            workspace_id, event.execution_id, event.execution_step_id,
        )
        return {
            "id": event.id,
            "execution_id": event.execution_id,
            **failed_node,
            **workflows.get(event.execution_id, {}),
            "execution_step_id": event.execution_step_id,
            "event_type": event.event_type,
            "attempts": event.attempts,
            "status": event.status,
            "error": event.error,
            "created_at": event.created_at,
            "resolved_at": event.resolved_at,
        }


    async def resolve_event(
        self,
        event_id: UUID,
        workspace_id: UUID,
    ) -> dict | None:
        event = await self.repository.resolve_event(
            event_id=event_id,
            workspace_id=workspace_id,
        )

        if event is None:
            return None

        await self.repository.session.commit()

        return {
            "id": event.id,
            "status": event.status,
            "resolved_at": event.resolved_at,
        }


    
    async def replay_event(
        self,
        event_id: UUID,
        workspace_id: UUID,
    ) -> dict:
        session = self.repository.session

        # 1. Read and validate the original failure.
        event = await self.repository.get_by_id(
            event_id=event_id,
            workspace_id=workspace_id,
        )

        if event is None:
            raise ValueError("not_found")

        if event.status != "pending":
            raise ValueError("already_handled")

        original = await session.scalar(
            select(Execution).where(
                Execution.id == event.execution_id,
                Execution.workspace_id == workspace_id,
                Execution.status == ExecutionStatus.FAILED,
            )
        )

        if original is None:
            raise ValueError("invalid_execution")

        if event.execution_step_id is None:
            raise ValueError("missing_failed_step")

        failed_step = await session.scalar(
            select(ExecutionStep).where(
                ExecutionStep.id == event.execution_step_id,
                ExecutionStep.execution_id == original.id,
                ExecutionStep.status == "failed",
            )
        )

        if failed_step is None:
            raise ValueError("invalid_failed_step")

        context = original.context

        if not isinstance(context, dict) or not all(
            isinstance(context.get(key), dict)
            for key in ("trigger", "variables", "nodes")
        ):
            raise ValueError("invalid_context")

        # Save primitive values before ending the transaction.
        original_id = original.id
        workflow_id = original.workflow_id
        version_id = original.workflow_version_id
        failed_step_id = failed_step.id
        failed_node_id = failed_step.node_id

        await session.rollback()

        # 2. Validate the original workflow graph.
        workflow_client = WorkflowClient()

        try:
            definition = await workflow_client.get_workflow_definition(
                workflow_id=str(workflow_id),
                version_id=str(version_id),
                workspace_id=str(workspace_id),
            )
        finally:
            await workflow_client.close()

        graph = ExecutionGraph(
            nodes=json.loads(definition.nodes_json),
            edges=json.loads(definition.edges_json),
        )

        if not validate_replay_path(
            graph,
            failed_node_id,
        ):
            raise ValueError("unsafe_replay")

        # 3. Lock the DLQ event and recheck its state.
        try:
            locked_event = await self.repository.get_pending_for_replay(
                event_id=event_id,
                workspace_id=workspace_id,
            )

            if locked_event is None:
                raise ValueError("already_handled")

            if (
                locked_event.execution_id != original_id
                or locked_event.execution_step_id != failed_step_id
            ):
                raise ValueError("invalid_failed_step")

            original = await session.scalar(
                select(Execution).where(
                    Execution.id == original_id,
                    Execution.workspace_id == workspace_id,
                    Execution.status == ExecutionStatus.FAILED,
                )
            )

            if original is None:
                raise ValueError("invalid_execution")

            if (
                original.workflow_id != workflow_id
                or original.workflow_version_id != version_id
            ):
                raise ValueError("workflow_changed")

            failed_step = await session.scalar(
                select(ExecutionStep).where(
                    ExecutionStep.id == failed_step_id,
                    ExecutionStep.execution_id == original.id,
                    ExecutionStep.node_id == failed_node_id,
                    ExecutionStep.status == "failed",
                )
            )

            if failed_step is None:
                raise ValueError("invalid_failed_step")

            context = original.context

            if not isinstance(context, dict) or not all(
                isinstance(context.get(key), dict)
                for key in ("trigger", "variables", "nodes")
            ):
                raise ValueError("invalid_context")

            # 4. Create a new pending replay execution.
            replay = Execution(
                id=uuid4(),
                workspace_id=workspace_id,
                workflow_id=original.workflow_id,
                workflow_version_id=original.workflow_version_id,
                workflow_name=original.workflow_name,
                trigger_type=original.trigger_type,
                trigger_data=original.trigger_data,
                context=context,
                replay_of_execution_id=original.id,
                replay_start_node_id=failed_node_id,
                status=ExecutionStatus.PENDING,
            )

            session.add(replay)

            # 5. Mark DLQ event as replayed.
            await self.repository.mark_replayed(locked_event)

            await session.commit()

            return {
                "execution_id": replay.id,
                "status": "accepted",
                "replay_of_execution_id": original_id,
            }

        except Exception:
            await session.rollback()
            raise

