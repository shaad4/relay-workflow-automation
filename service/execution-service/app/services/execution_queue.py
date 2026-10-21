import grpc
import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError

from app.grpc.workflow_client import WorkflowClient

from app.db.database import AsyncSessionLocal
from app.engine.exceptions import (
    HumanApprovalRequired,
    ActionExecutionFailed,
)
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.models.execution import Execution
from app.repositories.execution_queue import ExecutionQueueRepository
from app.kafka.lifecycle_producer import publish_lifecycle_event
from app.schemas.lifecycle_events import WorkflowLifecycleEvent


LEASE_SECONDS = 120
HEARTBEAT_INTERVAL_SECONDS = 30


async def publish_execution_lifecycle(
    event_type: str,
    execution_id: UUID,
    workspace_id: UUID,
    workflow_id: UUID,
    workflow_version_id: UUID,
) -> None:
    """Publish lifecycle events without failing the workflow."""

    try:
        event = WorkflowLifecycleEvent(
            event_type=event_type,
            execution_id=execution_id,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            workflow_version_id=workflow_version_id,
        )

        await publish_lifecycle_event(event)

    except Exception:
        # Lifecycle publishing is best-effort for the MVP.
        pass


async def create_pending_execution(event: dict) -> UUID:
    """
    Atomically create a pending execution and idempotency key.

    Duplicate events return the existing execution ID.
    No workflow execution happens here.
    """

    try:
        event_id = UUID(str(event["event_id"]))
        workspace_id = UUID(str(event["workspace_id"]))
        workflow_id = UUID(str(event["workflow_id"]))
        workflow_version_id = UUID(
            str(event["workflow_version_id"])
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid workflow event identifiers"
        ) from exc

    trigger_type = event.get("trigger_type")

    if trigger_type not in {
        "webhook",
        "manual",
        "schedule",
    }:
        raise ValueError(
            "Invalid workflow trigger type"
        )

    trigger_data = event.get("payload", {})

    if not isinstance(trigger_data, dict):
        raise ValueError(
            "Workflow event payload must be an object"
        )

    event_key = f"workflow.triggered:{event_id}"

    # Validate the workflow before accepting the event.
    workflow_client = WorkflowClient()

    try:
        validation = await workflow_client.validate_workflow_version(
            workflow_id=str(workflow_id),
            version_id=str(workflow_version_id),
            workspace_id=str(workspace_id),
        )

    except grpc.aio.AioRpcError as exc:
        raise RuntimeError(
            "Unable to validate workflow version"
        ) from exc

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


    async with AsyncSessionLocal() as session:
        repository = ExecutionQueueRepository(session)

        try:
            execution = await repository.create_pending(
                workspace_id=workspace_id,
                workflow_id=workflow_id,
                workflow_version_id=workflow_version_id,
                trigger_type=trigger_type,
                trigger_data=trigger_data,
                event_key=event_key,
            )

            execution_id = execution.id

            await session.commit()

            return execution_id

        except IntegrityError:
            await session.rollback()

            existing = await repository.get_by_event_key(
                workspace_id=workspace_id,
                key=event_key,
            )

            if existing is not None:
                return existing.id

            raise

        except Exception:
            await session.rollback()
            raise


async def claim_pending_execution(
    execution_id: UUID,
    worker_id: str,
    lease_seconds: int = LEASE_SECONDS,
) -> bool:
    """
    Atomically claim a pending execution.

    Only one worker can transition an execution
    from pending to running.
    """

    if not worker_id or len(worker_id) > 100:
        raise ValueError("Invalid worker ID")

    if not 1 <= lease_seconds <= 3600:
        raise ValueError(
            "lease_seconds must be between 1 and 3600"
        )

    async with AsyncSessionLocal() as session:
        repository = ExecutionQueueRepository(session)

        try:
            claimed = await repository.claim_pending(
                execution_id=execution_id,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
            )

            if not claimed:
                await session.rollback()
                return False

            await session.commit()
            return True

        except Exception:
            await session.rollback()
            raise


async def renew_execution_lease(
    execution_id: UUID,
    worker_id: str,
    lease_seconds: int = LEASE_SECONDS,
) -> bool:
    """Renew a running execution's lease."""

    async with AsyncSessionLocal() as session:
        repository = ExecutionQueueRepository(session)

        try:
            renewed = await repository.renew_lease(
                execution_id=execution_id,
                worker_id=worker_id,
                lease_seconds=lease_seconds,
            )

            if not renewed:
                await session.rollback()
                return False

            await session.commit()
            return True

        except Exception:
            await session.rollback()
            raise


async def execution_heartbeat(
    execution_id: UUID,
    worker_id: str,
    owner_task: asyncio.Task,
    interval_seconds: int = HEARTBEAT_INTERVAL_SECONDS,
    lease_seconds: int = LEASE_SECONDS,
) -> None:
    """
    Periodically renew the execution lease.

    If renewal fails, cancel the owning task
    to prevent continued execution.
    """

    if not 1 <= interval_seconds < lease_seconds:
        raise ValueError(
            "Invalid heartbeat interval"
        )

    try:
        while True:
            await asyncio.sleep(interval_seconds)

            try:
                renewed = await renew_execution_lease(
                    execution_id=execution_id,
                    worker_id=worker_id,
                    lease_seconds=lease_seconds,
                )

            except Exception:
                renewed = False

            if not renewed:
                owner_task.cancel()
                return

    except asyncio.CancelledError:
        raise


async def finalize_execution(
    execution_id: UUID,
    worker_id: str,
    status: str,
    *,
    context_data: dict | None = None,
    error: dict | None = None,
) -> bool:
    """
    Persist final execution state only when the worker
    still owns a valid lease.
    """

    async with AsyncSessionLocal() as session:
        try:
            values = {
                "status": status,
                "claimed_by": None,
                "heartbeat_at": None,
                "lease_expires_at": None,
            }

            if context_data is not None:
                values["context"] = context_data

            if error is not None:
                values["error"] = error

            if status in {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
            }:
                values["completed_at"] = datetime.now(
                    timezone.utc
                )

            statement = (
                update(Execution)
                .where(
                    Execution.id == execution_id,
                    Execution.claimed_by == worker_id,
                    Execution.status == ExecutionStatus.RUNNING,
                    Execution.lease_expires_at > func.now(),
                )
                .values(**values)
                .returning(Execution.id)
            )

            result = await session.execute(statement)

            finalized = (
                result.scalar_one_or_none() is not None
            )

            if not finalized:
                await session.rollback()
                return False

            await session.commit()
            return True

        except Exception:
            await session.rollback()
            raise


async def execute_pending_execution(
    execution_id: UUID,
) -> bool:
    """
    Claim and execute an existing pending execution.

    Returns False when another worker already claimed it.
    """

    worker_id = f"worker-{uuid4().hex}"

    claimed = await claim_pending_execution(
        execution_id=execution_id,
        worker_id=worker_id,
    )

    if not claimed:
        return False

    # Load execution metadata without holding the DB session
    # open during the workflow.
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Execution).where(
                Execution.id == execution_id,
                Execution.claimed_by == worker_id,
            )
        )

        execution = result.scalar_one_or_none()

        if execution is None:
            raise RuntimeError(
                "Claimed execution not found"
            )

        workflow_id = str(execution.workflow_id)
        workflow_version_id = str(
            execution.workflow_version_id
        )
        workspace_id = str(execution.workspace_id)
        trigger_data = execution.trigger_data

    owner_task = asyncio.current_task()

    if owner_task is None:
        raise RuntimeError(
            "Execution must run inside an asyncio task"
        )

    heartbeat_task = asyncio.create_task(
        execution_heartbeat(
            execution_id=execution_id,
            worker_id=worker_id,
            owner_task=owner_task,
        )
    )

    try:
        await publish_execution_lifecycle(
            event_type="workflow.started",
            execution_id=execution_id,
            workspace_id=UUID(workspace_id),
            workflow_id=UUID(workflow_id),
            workflow_version_id=UUID(workflow_version_id),
        )

    
        try:
            result = await run_execution(
                execution_id=execution_id,
                workflow_id=workflow_id,
                workflow_version_id=workflow_version_id,
                workspace_id=workspace_id,
                trigger_data=trigger_data,
            )

            final_status = ExecutionStatus.COMPLETED
            final_context = result["context"]
            final_error = None

        except HumanApprovalRequired:
            final_status = (
                ExecutionStatus.WAITING_FOR_APPROVAL
            )
            final_context = None
            final_error = None

        except ActionExecutionFailed as exc:
            final_status = ExecutionStatus.FAILED
            final_context = None
            final_error = {
                "node_id": exc.node_id,
                "message": "Action execution failed",
            }

        except asyncio.CancelledError:
            # Do not finalize a cancelled execution as completed
            # or failed. Recovery will handle the abandoned lease.
            raise

        except Exception:
            final_status = ExecutionStatus.FAILED
            final_context = None
            final_error = {
                "message": "Workflow execution failed",
            }

        finalized = await finalize_execution(
            execution_id=execution_id,
            worker_id=worker_id,
            status=final_status,
            context_data=final_context,
            error=final_error,
        )

        
        if not finalized:
            raise RuntimeError(
                "Execution lease expired or ownership was lost"
            )

        if final_status == ExecutionStatus.COMPLETED:
            await publish_execution_lifecycle(
                event_type="workflow.completed",
                execution_id=execution_id,
                workspace_id=UUID(workspace_id),
                workflow_id=UUID(workflow_id),
                workflow_version_id=UUID(workflow_version_id),
            )

        elif final_status == ExecutionStatus.FAILED:
            await publish_execution_lifecycle(
                event_type="workflow.failed",
                execution_id=execution_id,
                workspace_id=UUID(workspace_id),
                workflow_id=UUID(workflow_id),
                workflow_version_id=UUID(workflow_version_id),
            )

        return True


    finally:
        heartbeat_task.cancel()

        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass



async def inspect_recoverable_executions(
    limit: int = 100,
) -> dict:
    """
    Inspect pending and expired executions.

    Does not claim, retry, or modify any execution.
    """

    async with AsyncSessionLocal() as session:
        repository = ExecutionQueueRepository(session)

        pending = await repository.list_pending_executions(
            limit=limit,
        )

        expired = await repository.list_expired_executions(
            limit=limit,
        )

        return {
            "pending": [
                {
                    "execution_id": str(item.id),
                    "workspace_id": str(item.workspace_id),
                    "status": item.status,
                }
                for item in pending
            ],
            "expired": [
                {
                    "execution_id": str(item.id),
                    "workspace_id": str(item.workspace_id),
                    "status": item.status,
                    "claimed_by": item.claimed_by,
                    "lease_expires_at": (
                        item.lease_expires_at.isoformat()
                        if item.lease_expires_at
                        else None
                    ),
                    "recovery_status": "requires_review",
                }
                for item in expired
            ],
        }
