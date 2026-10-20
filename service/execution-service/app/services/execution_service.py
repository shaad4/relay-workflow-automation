from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

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


async def _update_execution_status(
    execution_id: UUID,
    status: str,
    *,
    context_data: dict | None = None,
    error: dict | None = None,
):
    """Update execution state using a short-lived DB session."""

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Execution).where(
                    Execution.id == execution_id,
                )
            )

            execution = result.scalar_one_or_none()

            if execution is None:
                raise ValueError("Execution not found")

            execution.status = status

            if context_data is not None:
                execution.context = context_data

            if error is not None:
                execution.error = error

            if status in {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
            }:
                execution.completed_at = datetime.now(
                    timezone.utc
                )

            await _commit_session(session)

        except Exception:
            await session.rollback()
            raise


async def create_execution(event: dict) -> Execution:
    """Create and execute a workflow without holding a DB session open."""

    # 1. Validate workflow version.
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

    # 2. Create execution using a short-lived session.
    async with AsyncSessionLocal() as session:
        execution = Execution(
            workspace_id=UUID(event["workspace_id"]),
            workflow_id=UUID(event["workflow_id"]),
            workflow_version_id=UUID(
                event["workflow_version_id"]
            ),
            status=ExecutionStatus.PENDING,
            trigger_type=event.get("trigger_type", "webhook"),
            trigger_data=event.get("payload"),
            context={},
            started_at=datetime.now(timezone.utc),
        )

        session.add(execution)

        await _commit_session(session)
        await session.refresh(execution)

        execution_id = execution.id

    # 3. Mark execution as running.
    await _update_execution_status(
        execution_id,
        ExecutionStatus.RUNNING,
    )

    # 4. Execute without holding the outer DB session.
    try:
        result = await run_execution(
            execution_id=execution_id,
            workflow_id=event["workflow_id"],
            workflow_version_id=event["workflow_version_id"],
            workspace_id=event["workspace_id"],
            trigger_data=event.get("payload"),
        )

        await _update_execution_status(
            execution_id,
            ExecutionStatus.COMPLETED,
            context_data=result["context"],
        )

    except HumanApprovalRequired:
        await _update_execution_status(
            execution_id,
            ExecutionStatus.WAITING_FOR_APPROVAL,
        )

    except ActionExecutionFailed as exc:
        await _update_execution_status(
            execution_id,
            ExecutionStatus.FAILED,
            error={
                "node_id": exc.node_id,
                "message": "Action execution failed",
            },
        )

    except Exception:
        await _update_execution_status(
            execution_id,
            ExecutionStatus.FAILED,
            error={
                "message": "Workflow execution failed",
            },
        )

    # 5. Return a fresh execution record.
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Execution).where(
                Execution.id == execution_id,
            )
        )

        execution = result.scalar_one_or_none()

        if execution is None:
            raise ValueError("Execution not found")

        return execution
