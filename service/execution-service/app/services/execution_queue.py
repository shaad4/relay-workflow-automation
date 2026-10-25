import grpc
import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update, func, case, literal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from app.engine.error_classifier import classify_error
from app.grpc.workflow_client import WorkflowClient

from app.db.database import AsyncSessionLocal
from app.engine.exceptions import (
    HumanApprovalRequired,
    ActionExecutionFailed,
    ExecutionCancellationRequested,
)
from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.models.execution import Execution
from app.repositories.execution_queue import ExecutionQueueRepository
from app.kafka.lifecycle_producer import publish_lifecycle_event
from app.schemas.lifecycle_events import WorkflowLifecycleEvent

from app.models.dead_letter_event import DeadLetterEvent
from app.models.execution_step import ExecutionStep
from app.engine.step_status import ExecutionStepStatus

from app.models.human_approval import HumanApproval
from app.engine.approval_status import HumanApprovalStatus


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
) -> str | None:
    """
    Finalize only when this worker owns a valid lease.

    Returns the actual persisted status, or None
    if ownership was lost.
    """

    async with AsyncSessionLocal() as session:
        try:
            actual_status = case(
                (
                    Execution.cancel_requested_at.is_not(None),
                    ExecutionStatus.CANCELLED,
                ),
                else_=status,
            )

            values = {
                "status": actual_status,
                "claimed_by": None,
                "heartbeat_at": None,
                "lease_expires_at": None,
            }

            if context_data is not None:
                values["context"] = context_data

            values["error"] = case(
                (
                    Execution.cancel_requested_at.is_not(None),
                    None,
                ),
                # CASE values need their own type: dicts require JSON encoding,
                # and an all-NULL CASE otherwise resolves to text in PostgreSQL.
                else_=literal(error, type_=JSONB(none_as_null=True)),
            )

            if status in {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            }:
                values["completed_at"] = func.now()
            else:
                values["completed_at"] = case(
                    (
                        Execution.cancel_requested_at.is_not(None),
                        func.now(),
                    ),
                    else_=Execution.completed_at,
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
                .returning(
                    Execution.status,
                    Execution.workspace_id,
                )
            )

            result = await session.execute(statement)
            row = result.one_or_none()

            if row is None:
                await session.rollback()
                return None

            persisted_status = row.status

            if persisted_status == ExecutionStatus.CANCELLED:
                await session.execute(
                    update(HumanApproval)
                    .where(
                        HumanApproval.execution_id == execution_id,
                        HumanApproval.workspace_id == row.workspace_id,
                        HumanApproval.status == HumanApprovalStatus.PENDING,
                    )
                    .values(
                        status=HumanApprovalStatus.CANCELLED,
                    )
                )

                await session.execute(
                    update(ExecutionStep)
                    .where(
                        ExecutionStep.execution_id == execution_id,
                        ExecutionStep.status.in_([
                            ExecutionStepStatus.PENDING,
                            ExecutionStepStatus.RUNNING,
                            ExecutionStepStatus.WAITING_FOR_APPROVAL,
                        ]),
                    )
                    .values(
                        status=ExecutionStepStatus.CANCELLED,
                        completed_at=func.now(),
                    )
                )

            if persisted_status == ExecutionStatus.FAILED:
                step_result = await session.execute(
                    select(ExecutionStep)
                    .where(
                        ExecutionStep.execution_id == execution_id,
                        ExecutionStep.status == ExecutionStepStatus.FAILED,
                    )
                    .order_by(ExecutionStep.sequence.desc())
                    .limit(1)
                )

                failed_step = step_result.scalar_one_or_none()

                dead_letter = DeadLetterEvent(
                    workspace_id=row.workspace_id,
                    execution_id=execution_id,
                    execution_step_id=(
                        failed_step.id if failed_step else None
                    ),
                    event_type="workflow.failed",
                    payload=None,
                    error=error or {
                        "message": "Workflow execution failed"
                    },
                    attempts=(
                        failed_step.attempt if failed_step else 1
                    ),
                    status="pending",
                )

                session.add(dead_letter)

            await session.commit()
            return persisted_status

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
        
        
        # Check for an approval resume checkpoint.
        saved_context = execution.context or {}
        if isinstance(saved_context, str):
            saved_context = json.loads(saved_context)
        resume_data = saved_context.get("_resume")

        
        if "_resume" in saved_context:
            if (
                not isinstance(resume_data, dict)
                or resume_data.get("state") != "pending"
                or "start_node_id" not in resume_data
                or (
                    resume_data["start_node_id"] is not None
                    and (
                        not isinstance(
                            resume_data["start_node_id"], str
                        )
                        or not resume_data["start_node_id"].strip()
                    )
                )
            ):
                persisted_status = await finalize_execution(
                    execution_id=execution_id,
                    worker_id=worker_id,
                    status=ExecutionStatus.FAILED,
                    error={
                        "error_code": "INVALID_RESUME_CHECKPOINT",
                        "message": "Invalid approval resume checkpoint",
                        "requires_review": True,
                    },
                )

                if persisted_status is None:
                    raise RuntimeError(
                        "Unable to finalize invalid resume checkpoint"
                    )

                return True



        if resume_data is not None:
            # Resume after the human approval node.
            start_node_id = resume_data.get("start_node_id")

            # Keep the workflow's previous outputs,
            # but remove the consumed resume checkpoint.
            execution_context = {
                **saved_context,
            }
            execution_context.pop("_resume", None)

        elif execution.replay_start_node_id is not None:
            # Resume a safe DLQ replay.
            start_node_id = execution.replay_start_node_id
            execution_context = saved_context

        else:
            # Normal workflow starts from its trigger.
            start_node_id = None
            execution_context = None


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
            if resume_data is not None and start_node_id is None:
                # Approval was the final workflow node.
                # Nothing else needs to execute.
                final_status = ExecutionStatus.COMPLETED
                final_context = execution_context
                final_error = None

            else:
                result = await run_execution(
                    execution_id=execution_id,
                    workflow_id=workflow_id,
                    workflow_version_id=workflow_version_id,
                    workspace_id=workspace_id,
                    trigger_data=trigger_data,
                    context_data=execution_context,
                    start_node_id=start_node_id,
                )

                final_status = ExecutionStatus.COMPLETED
                final_context = result["context"]
                final_error = None
        except ExecutionCancellationRequested:
            final_status = ExecutionStatus.CANCELLED
            final_context = None
            final_error = None


        except HumanApprovalRequired:
            # The runner committed the approval, waiting step, and execution
            # together and released its lease. Do not finalize again: a user
            # may already have recorded a decision and queued the next branch.
            return True

        except ActionExecutionFailed as exc:
            final_status = ExecutionStatus.FAILED
            final_context = None
            final_error = classify_error(exc)

        except asyncio.CancelledError:
            # Do not finalize a cancelled execution as completed
            # or failed. Recovery will handle the abandoned lease.
            raise

        except Exception as exc:
            final_status = ExecutionStatus.FAILED
            final_context = None
            final_error = classify_error(exc)

        persisted_status = await finalize_execution(
            execution_id=execution_id,
            worker_id=worker_id,
            status=final_status,
            context_data=final_context,
            error=final_error,
        )

        
        if persisted_status is None:
            raise RuntimeError(
                "Execution lease expired or ownership was lost"
            )

        if persisted_status == ExecutionStatus.COMPLETED:
            await publish_execution_lifecycle(
                event_type="workflow.completed",
                execution_id=execution_id,
                workspace_id=UUID(workspace_id),
                workflow_id=UUID(workflow_id),
                workflow_version_id=UUID(workflow_version_id),
            )

        elif persisted_status == ExecutionStatus.FAILED:
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



async def cleanup_expired_executions(
    limit: int = 100,
) -> int:
    """
    Mark expired running executions and their unfinished
    steps as failed.

    Does not restart workflows or replay external actions.
    """

    if not 1 <= limit <= 100:
        raise ValueError(
            "Limit must be between 1 and 100"
        )

    cleaned_count = 0

    async with AsyncSessionLocal() as session:
        repository = ExecutionQueueRepository(session)

        expired = await repository.list_expired_executions(
            limit=limit,
        )

        for execution in expired:
            try:
                execution_id = execution.id
                workspace_id = execution.workspace_id

                claimed = await repository.mark_expired_as_failed(
                    execution_id=execution_id,
                    workspace_id=workspace_id,
                )

                if not claimed:
                    await session.rollback()
                    continue

                # Mark only unfinished steps as interrupted.
                statement = (
                    update(ExecutionStep)
                    .where(
                        ExecutionStep.execution_id == execution_id,
                        ExecutionStep.status.in_([
                            ExecutionStepStatus.PENDING,
                            ExecutionStepStatus.RUNNING,
                        ]),
                    )
                    .values(
                        status=ExecutionStepStatus.FAILED,
                        completed_at=func.now(),
                        error={
                            "error_code": "WORKER_INTERRUPTED",
                            "message": (
                                "Step interrupted because "
                                "the worker lease expired"
                            ),
                            "requires_review": True,
                        },
                    )
                )

                await session.execute(statement)

                # Commit execution and step updates together.
                await session.commit()

                cleaned_count += 1

            except Exception:
                await session.rollback()
                raise

    return cleaned_count




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
