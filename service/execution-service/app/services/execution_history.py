from uuid import UUID

from app.repositories.execution import ExecutionRepository


class ExecutionHistoryService:
    def __init__(self, repository: ExecutionRepository):
        self.repository = repository

    async def list_executions(
        self,
        workspace_id: UUID,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
    ) -> dict:
        try:
            executions, total = (
                await self.repository.list_executions(
                    workspace_id=workspace_id,
                    page=page,
                    page_size=page_size,
                    status=status,
                )
            )

            items = []

            for execution in executions:
                duration_ms = None

                if (
                    execution.started_at is not None
                    and execution.completed_at is not None
                ):
                    duration_ms = max(
                        0,
                        int(
                            (
                                execution.completed_at
                                - execution.started_at
                            ).total_seconds() * 1000
                        ),
                    )

                items.append(
                    {
                        "id": execution.id,
                        "workflow_id": execution.workflow_id,
                        "workflow_version_id": (
                            execution.workflow_version_id
                        ),
                        "status": execution.status,
                        "trigger_type": execution.trigger_type,
                        "started_at": execution.started_at,
                        "completed_at": execution.completed_at,
                        "created_at": execution.created_at,
                        "duration_ms": duration_ms,
                    }
                )

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        except RuntimeError:
            raise

    
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

        duration_ms = None

        if (
            execution.started_at is not None
            and execution.completed_at is not None
        ):
            duration_ms = max(
                0,
                int(
                    (
                        execution.completed_at
                        - execution.started_at
                    ).total_seconds() * 1000
                ),
            )

        return {
            "id": execution.id,
            "workspace_id": execution.workspace_id,
            "workflow_id": execution.workflow_id,
            "workflow_version_id": execution.workflow_version_id,
            "status": execution.status,
            "trigger_type": execution.trigger_type,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "created_at": execution.created_at,
            "duration_ms": duration_ms,
            "error": execution.error,
        }

