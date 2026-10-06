from datetime import datetime, timezone
from uuid import UUID

from app.db.database import AsyncSessionLocal
from app.engine.exceptions import HumanApprovalRequired, ActionExecutionFailed
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.grpc.workflow_client import WorkflowClient
from app.models.execution import Execution


async def create_execution(event: dict) -> Execution:
    workflow_client = WorkflowClient()
    try:
        validation = await workflow_client.validate_workflow_version(
            workflow_id=event["workflow_id"],
            version_id=event["workflow_version_id"],
            workspace_id=event["workspace_id"],
        )
    finally:
        await workflow_client.close()

    if not validation.valid:
        raise ValueError("Workflow or workflow version not found")
    if validation.status.lower() != "published":
        raise ValueError("Workflow version is not published")
    if validation.workflow_status.lower() != "active":
        raise ValueError("Workflow is inactive")

    async with AsyncSessionLocal() as session:
        try:
            execution = Execution(
                workspace_id=UUID(event["workspace_id"]),
                workflow_id=UUID(event["workflow_id"]),
                workflow_version_id=UUID(event["workflow_version_id"]),
                status=ExecutionStatus.PENDING,
                trigger_type=event["event_type"],
                trigger_data=event.get("payload"),
                context={},
                started_at=datetime.now(timezone.utc),
            )

            session.add(execution)

            await session.commit()
            await session.refresh(execution)

            execution.status = ExecutionStatus.RUNNING
            await session.commit()

            try:
                await run_execution(
                    execution_id=execution.id,
                    workflow_id=event["workflow_id"],
                    workflow_version_id=event["workflow_version_id"],
                    workspace_id=event["workspace_id"],
                    trigger_data=event.get("payload"),
                )

            except HumanApprovalRequired:
                execution.status = ExecutionStatus.WAITING_FOR_APPROVAL
                await session.commit()

                return execution

            except ActionExecutionFailed as exc:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.now(timezone.utc)
                execution.error = {
                    "node_id": exc.node_id,
                    "message": exc.error,
                }

                await session.commit()

                return execution

            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)

            await session.commit()

            return execution

        except Exception:
            await session.rollback()
            raise