from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.human_approval import HumanApproval
from app.engine.approval_status import HumanApprovalStatus


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
                HumanApproval.status == "pending",
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