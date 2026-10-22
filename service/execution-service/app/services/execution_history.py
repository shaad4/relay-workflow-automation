from uuid import UUID

from app.repositories.execution import ExecutionRepository
from app.utils.payload_sanitizer import sanitize_payload


class ExecutionHistoryService:
    def __init__(self, repository: ExecutionRepository):
        self.repository = repository

    async def list_executions(
        self,
        workspace_id: UUID,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
        group_replays: bool = False,
        group_id: UUID | None = None,
    ) -> dict | None:
        if group_id is not None:
            result = await self.repository.list_execution_attempts(
                workspace_id, group_id, page, page_size,
            )
            if result is None:
                return None
            executions, total, root_id = result
            items = [self.serialize_execution(execution) | {
                "execution_group_id": root_id, "attempt_count": total,
            } for execution in executions]
        elif group_replays:
            groups, total = await self.repository.list_execution_groups(
                workspace_id, page, page_size, status,
            )
            items = [self.serialize_execution(execution) | {
                "execution_group_id": root_id, "attempt_count": count,
            } for execution, root_id, count in groups]
        else:
            executions, total = await self.repository.list_executions(
                workspace_id=workspace_id, page=page, page_size=page_size, status=status,
            )
            items = [self.serialize_execution(execution) for execution in executions]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_execution_by_id(
        self,
        execution_id: UUID,
        workspace_id: UUID,
    ) -> dict | None:
        execution = await self.repository.get_execution_by_id(
            execution_id=execution_id,
            workspace_id=workspace_id,
        )

        if execution is None:
            return None

        return self.serialize_execution(execution) | {
            "workspace_id": execution.workspace_id,
            "error": sanitize_payload(execution.error),
        }

    @staticmethod
    def serialize_execution(execution):
        duration_ms = None
        if execution.started_at is not None and execution.completed_at is not None:
            duration_ms = max(0, int((execution.completed_at - execution.started_at).total_seconds() * 1000))
        return {
            "id": execution.id,
            "workflow_id": execution.workflow_id,
            "workflow_version_id": execution.workflow_version_id,
            "workflow_name": execution.workflow_name,
            "status": execution.status,
            "trigger_type": execution.trigger_type,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "created_at": execution.created_at,
            "duration_ms": duration_ms,
            "replay_of_execution_id": execution.replay_of_execution_id,
        }


    async def list_execution_steps(
        self,
        execution_id: UUID,
        workspace_id: UUID,
    ) -> list[dict] | None:
        steps = await self.repository.list_execution_steps(
            execution_id=execution_id,
            workspace_id=workspace_id,
        )

        if steps is None:
            return None

        return [
            {
                "id": step.id,
                "execution_id": step.execution_id,
                "node_id": step.node_id,
                "node_name": step.node_name,
                "node_type": step.node_type,
                "status": step.status,
                "sequence": step.sequence,
                "attempt": step.attempt,
                "input": sanitize_payload(step.input),
                "output": sanitize_payload(step.output),
                "error": sanitize_payload(step.error),
                "started_at": step.started_at,
                "completed_at": step.completed_at,
                "duration_ms": step.duration_ms,
                "created_at": step.created_at,
            }
            for step in steps
        ]
