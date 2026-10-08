
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.human_approval import HumanApproval
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep

from app.engine.approval_status import HumanApprovalStatus
from app.engine.status import ExecutionStatus
from app.engine.step_status import ExecutionStepStatus

from app.services.approval_branch_service import resolve_approval_branch


@dataclass(frozen=True)
class ApprovalDecisionResult:
    approval: HumanApproval
    execution_id: UUID
    approval_node_id: str
    decision: str
    context_data: dict
    start_node_id: str | None


async def list_pending_approvals(
    workspace_id: str,
    approver_user_id: str,
    session: AsyncSession,
) -> list[HumanApproval]:
    try:
        result = await session.execute(
            select(HumanApproval)
            .where(
                HumanApproval.workspace_id == workspace_id,
                HumanApproval.approver_user_id == approver_user_id,
                HumanApproval.status == HumanApprovalStatus.PENDING,
            )
            .order_by(HumanApproval.created_at.desc())
        )

        return list(result.scalars().all())

    except Exception:
        await session.rollback()
        raise


async def get_approval(
    approval_id: UUID,
    workspace_id: str,
    approver_user_id: str,
    session: AsyncSession,
) -> HumanApproval | None:
    try:
        result = await session.execute(
            select(HumanApproval)
            .where(
                HumanApproval.id == approval_id,
                HumanApproval.workspace_id == workspace_id,
                HumanApproval.approver_user_id == approver_user_id,
            )
        )

        return result.scalar_one_or_none()

    except Exception:
        await session.rollback()
        raise


async def approve_approval(
    approval_id: UUID,
    workspace_id: str,
    approver_user_id: str,
    session: AsyncSession,
) -> HumanApproval:
    try:
        result = await session.execute(
            select(HumanApproval)
            .where(
                HumanApproval.id == approval_id,
                HumanApproval.workspace_id == workspace_id,
                HumanApproval.approver_user_id == approver_user_id,
            )
            .with_for_update()
        )

        approval = result.scalar_one_or_none()

        if approval is None:
            raise ValueError("Approval not found")

        if approval.status != HumanApprovalStatus.PENDING:
            raise ValueError(
                f"Approval is already {approval.status}"
            )

        approval.status = HumanApprovalStatus.APPROVED
        approval.decision = "approved"
        approval.decided_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(approval)

        return approval

    except Exception:
        await session.rollback()
        raise


async def reject_approval(
    approval_id: UUID,
    workspace_id: str,
    approver_user_id: str,
    session: AsyncSession,
) -> HumanApproval:
    try:
        result = await session.execute(
            select(HumanApproval)
            .where(
                HumanApproval.id == approval_id,
                HumanApproval.workspace_id == workspace_id,
                HumanApproval.approver_user_id == approver_user_id,
            )
            .with_for_update()
        )

        approval = result.scalar_one_or_none()

        if approval is None:
            raise ValueError("Approval not found")

        if approval.status != HumanApprovalStatus.PENDING:
            raise ValueError(
                f"Approval is already {approval.status}"
            )

        approval.status = HumanApprovalStatus.REJECTED
        approval.decision = "rejected"
        approval.decided_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(approval)

        return approval

    except Exception:
        await session.rollback()
        raise


async def decide_approval(
    approval_id: UUID,
    workspace_id: str,
    approver_user_id: str,
    decision: str,
    session: AsyncSession,
) -> ApprovalDecisionResult:
    if decision not in {"approved", "rejected"}:
        raise ValueError("Invalid approval decision")

    try:
        result = await session.execute(
            select(HumanApproval)
            .where(
                HumanApproval.id == approval_id,
                HumanApproval.workspace_id == UUID(workspace_id),
                HumanApproval.approver_user_id == UUID(approver_user_id),
            )
            .with_for_update()
        )

        approval = result.scalar_one_or_none()

        if approval is None:
            raise ValueError("Approval not found")

        if approval.status != HumanApprovalStatus.PENDING:
            raise ValueError(
                f"Approval is already {approval.status}"
            )

        execution = await session.get(
            Execution,
            approval.execution_id,
            with_for_update=True,
        )

        if (
            execution is None
            or execution.workspace_id != UUID(workspace_id)
        ):
            raise ValueError("Execution not found")

        if execution.status != ExecutionStatus.WAITING_FOR_APPROVAL:
            raise ValueError(
                "Execution is not waiting for approval"
            )

        execution_step = await session.get(
            ExecutionStep,
            approval.execution_step_id,
            with_for_update=True,
        )

        if (
            execution_step is None
            or execution_step.execution_id != execution.id
            or execution_step.status
            != ExecutionStepStatus.WAITING_FOR_APPROVAL
        ):
            raise ValueError(
                "Approval execution step is not waiting"
            )

        # Resolve the matching approval edge before committing.
        start_node_id = await resolve_approval_branch(
            workflow_id=str(execution.workflow_id),
            workflow_version_id=str(execution.workflow_version_id),
            workspace_id=str(execution.workspace_id),
            approval_node_id=execution_step.node_id,
            decision=decision,
        )

        completed_at = datetime.now(timezone.utc)

        approval.status = (
            HumanApprovalStatus.APPROVED
            if decision == "approved"
            else HumanApprovalStatus.REJECTED
        )
        approval.decision = decision
        approval.decided_at = completed_at

        execution_step.status = ExecutionStepStatus.COMPLETED
        execution_step.completed_at = completed_at

        if execution_step.started_at:
            execution_step.duration_ms = int(
                (
                    completed_at - execution_step.started_at
                ).total_seconds() * 1000
            )

        execution.status = ExecutionStatus.RUNNING

        # Persist the selected branch for resume/recovery.
        context_data = dict(execution.context or {})

        context_data["_resume"] = {
            "approval_id": str(approval.id),
            "start_node_id": start_node_id,
            "decision": decision,
            "state": "pending",
        }

        execution.context = context_data

        decision_result = ApprovalDecisionResult(
            approval=approval,
            execution_id=execution.id,
            approval_node_id=execution_step.node_id,
            decision=decision,
            context_data=context_data,
            start_node_id=start_node_id,
        )

        await session.commit()
        await session.refresh(approval)

        return decision_result

    except Exception:
        await session.rollback()
        raise
