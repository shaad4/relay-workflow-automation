from datetime import datetime, timezone
from uuid import UUID

from app.db.database import AsyncSessionLocal
from app.engine.exceptions import (
    HumanApprovalRequired,
    ActionExecutionFailed,
)
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.grpc.workflow_client import WorkflowClient
from app.models.execution import Execution


async def _commit_session(session):
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def create_execution(event: dict) -> Execution:

    # 1. Validate workflow and version
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
        raise ValueError(
            "Workflow or workflow version not found"
        )

    if validation.status.lower() != "published":
        raise ValueError(
            "Workflow version is not published"
        )

    if validation.workflow_status.lower() != "active":
        raise ValueError(
            "Workflow is inactive"
        )

    # 2. Create execution record
    async with AsyncSessionLocal() as session:

        execution = Execution(
            workspace_id=UUID(event["workspace_id"]),
            workflow_id=UUID(event["workflow_id"]),
            workflow_version_id=UUID(
                event["workflow_version_id"]
            ),
            status=ExecutionStatus.PENDING,
            trigger_type=event["event_type"],
            trigger_data=event.get("payload"),
            context={},
            started_at=datetime.now(timezone.utc),
        )

        session.add(execution)

        await _commit_session(session)
        await session.refresh(execution)

        # 3. Mark execution as running
        execution.status = ExecutionStatus.RUNNING
        await _commit_session(session)

        result = None
        try:
            # 4. Execute workflow
            result = await run_execution(
                execution_id=execution.id,
                workflow_id=event["workflow_id"],
                workflow_version_id=event["workflow_version_id"],
                workspace_id=event["workspace_id"],
                trigger_data=event.get("payload"),
            )

            execution.context = result["context"]
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            await _commit_session(session)

        except HumanApprovalRequired:
            # 5. Pause execution for human approval
            await session.rollback()
            await session.refresh(execution)

            execution.status = (
                ExecutionStatus.WAITING_FOR_APPROVAL
            )

            await _commit_session(session)

            return execution

        except ActionExecutionFailed as exc:
            # 6. Handle known action failure
            await session.rollback()
            await session.refresh(execution)

            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.now(
                timezone.utc
            )

            execution.error = {
                "node_id": exc.node_id,
                "message": exc.error,
            }

            await _commit_session(session)

            return execution

        except Exception:
            # 7. Handle unexpected execution failure
            await session.rollback()
            await session.refresh(execution)

            if result is not None:
                execution.context = result["context"]
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.now(
                timezone.utc
            )

            execution.error = {
                "message": "Workflow execution failed",
            }

            await _commit_session(session)

            return execution

        return execution
