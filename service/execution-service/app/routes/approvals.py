from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_identity
from app.db.database import AsyncSessionLocal
from app.schemas.approvals import ApprovalListResponse, ApprovalResponse

from app.engine.runner import run_execution
from app.engine.status import ExecutionStatus
from app.engine.exceptions import (
    HumanApprovalRequired,
    ActionExecutionFailed,
)

from app.models.execution import Execution

from app.services.approval_service import (
    decide_approval,
    list_pending_approvals,
    get_approval,
)


router = APIRouter(
    prefix="/approvals",
    tags=["Approvals"],
)


async def _commit_session(session: AsyncSession) -> None:
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise


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


async def _handle_approval_decision(
    approval_id: UUID,
    decision: str,
    identity: dict,
    session: AsyncSession,
) -> ApprovalResponse:
    try:
        result = await decide_approval(
            approval_id=approval_id,
            workspace_id=identity["workspace_id"],
            approver_user_id=identity["user_id"],
            decision=decision,
            session=session,
        )

    except ValueError as exc:
        if str(exc) in {
            "Approval not found",
            "Execution not found",
        }:
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    approval = result.approval

    execution = await session.get(
        Execution,
        result.execution_id,
    )

    if execution is None:
        raise HTTPException(
            status_code=404,
            detail="Execution not found",
        )


    start_node_id = result.start_node_id

    # No outgoing edge: the workflow ends here.
    if start_node_id is None:
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)

        await _commit_session(session)

        return ApprovalResponse.model_validate(approval)

    try:
        await run_execution(
            execution_id=execution.id,
            workflow_id=str(execution.workflow_id),
            workflow_version_id=str(execution.workflow_version_id),
            workspace_id=str(execution.workspace_id),
            start_node_id=start_node_id,
            context_data=result.context_data,
        )

    except HumanApprovalRequired:
        execution.status = ExecutionStatus.WAITING_FOR_APPROVAL

        await _commit_session(session)

        return ApprovalResponse.model_validate(approval)

    except ActionExecutionFailed as exc:
        execution.status = ExecutionStatus.FAILED
        execution.completed_at = datetime.now(timezone.utc)
        execution.error = {
            "node_id": exc.node_id,
            "message": exc.error,
        }

        await _commit_session(session)

        return ApprovalResponse.model_validate(approval)

    execution.status = ExecutionStatus.COMPLETED
    execution.completed_at = datetime.now(timezone.utc)

    await _commit_session(session)

    return ApprovalResponse.model_validate(approval)


@router.post(
    "/{approval_id}/approve/",
    response_model=ApprovalResponse,
)
async def approve(
    approval_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    return await _handle_approval_decision(
        approval_id=approval_id,
        decision="approved",
        identity=identity,
        session=session,
    )


@router.post(
    "/{approval_id}/reject/",
    response_model=ApprovalResponse,
)
async def reject(
    approval_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    return await _handle_approval_decision(
        approval_id=approval_id,
        decision="rejected",
        identity=identity,
        session=session,
    )
