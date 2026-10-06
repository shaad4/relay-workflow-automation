from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.approval_status import HumanApprovalStatus
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.models.human_approval import HumanApproval


async def get_resume_state(
    execution_id: UUID,
    session: AsyncSession,
) -> tuple[Execution, list[ExecutionStep], int]:
    try:
        execution = await session.get(
            Execution,
            execution_id,
        )

        if execution is None:
            raise ValueError("Execution not found")

        result = await session.execute(
            select(ExecutionStep)
            .where(
                ExecutionStep.execution_id == execution_id,
            )
            .order_by(ExecutionStep.sequence.asc())
        )

        steps = list(result.scalars().all())

        approval_result = await session.execute(
            select(HumanApproval)
            .where(
                HumanApproval.execution_id == execution_id,
                HumanApproval.status == HumanApprovalStatus.APPROVED,
            )
            .order_by(HumanApproval.created_at.desc())
        )

        approval = approval_result.scalars().first()

        if approval is None:
            raise ValueError("Approved human approval not found")

        approval_step = next(
            (
                step
                for step in steps
                if step.id == approval.execution_step_id
            ),
            None,
        )

        if approval_step is None:
            raise ValueError(
                "Human approval execution step not found"
            )

        return execution, steps, approval_step.sequence

    except Exception:
        await session.rollback()
        raise