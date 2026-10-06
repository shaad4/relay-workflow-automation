from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_identity
from app.db.database import AsyncSessionLocal
from app.schemas.approvals import ApprovalListResponse, ApprovalResponse
from app.engine.runner import run_execution
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.engine.status import ExecutionStatus
from app.engine.step_status import ExecutionStepStatus
from app.engine.exceptions import HumanApprovalRequired
from app.services.approval_service import (
    approve_approval,
    list_pending_approvals,
    get_approval,
)


router = APIRouter(
    prefix="/approvals",
    tags=["Approvals"],
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/", response_model=ApprovalListResponse)
async def get_approvals(
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    approvals = await list_pending_approvals(
        workspace_id=identity["workspace_id"],
        approver_user_id=identity["user_id"],
        session=session,
    )

    return ApprovalListResponse(
        approvals=[
            ApprovalResponse.model_validate(approval)
            for approval in approvals
        ]
    )


@router.get("/{approval_id}/", response_model=ApprovalResponse)
async def get_approval_details(
    approval_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    approval = await get_approval(
        approval_id=approval_id,
        workspace_id=identity["workspace_id"],
        approver_user_id=identity["user_id"],
        session=session,
    )

    if approval is None:
        raise HTTPException(
            status_code=404,
            detail="Approval not found",
        )

    return ApprovalResponse.model_validate(approval)


@router.post("/{approval_id}/approve/", response_model=ApprovalResponse)
async def approve(
    approval_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        approval = await approve_approval(
            approval_id=approval_id,
            workspace_id=identity["workspace_id"],
            approver_user_id=identity["user_id"],
            session=session,
        )

    except ValueError as exc:
        if str(exc) == "Approval not found":
            raise HTTPException(
                status_code=404,
                detail="Approval not found",
            )

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    execution = await session.get(
        Execution,
        approval.execution_id,
    )

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail="Execution not found",
        )

    execution_step = await session.get(
        ExecutionStep,
        approval.execution_step_id,
    )

    if execution_step is None:
        raise HTTPException(
            status_code=404,
            detail="Execution step not found",
        )

    # The human approval step has now been successfully approved.
    completed_at = datetime.now(timezone.utc)

    execution_step.status = ExecutionStepStatus.COMPLETED
    execution_step.completed_at = completed_at

    if execution_step.started_at:
        execution_step.duration_ms = int(
            (
                completed_at - execution_step.started_at
            ).total_seconds()
            * 1000
        )

    # The workflow is about to resume.
    execution.status = ExecutionStatus.RUNNING

    await session.commit()

    try:
        await run_execution(
            execution_id=execution.id,
            workflow_id=str(execution.workflow_id),
            workflow_version_id=str(execution.workflow_version_id),
            workspace_id=str(execution.workspace_id),
            resume_from_sequence=execution_step.sequence,
            context_data=execution.context,
        )

    except HumanApprovalRequired:
        execution.status = ExecutionStatus.WAITING_FOR_APPROVAL
        await session.commit()

        return ApprovalResponse.model_validate(approval)

    execution.status = ExecutionStatus.COMPLETED
    execution.completed_at = datetime.now(timezone.utc)

    await session.commit()

    return ApprovalResponse.model_validate(approval)