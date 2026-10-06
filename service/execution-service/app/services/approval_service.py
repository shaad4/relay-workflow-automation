from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.human_approval import HumanApproval


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