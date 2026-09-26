from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate


async def create_workflow(
    data: WorkflowCreate,
    workspace_id: str,
    session: AsyncSession,
) -> Workflow:
    workflow = Workflow(
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
    )

    session.add(workflow)

    await session.commit()
    await session.refresh(workflow)

    return workflow


async def list_workflows(
    workspace_id: str,
    session: AsyncSession,
) -> list[Workflow]:
    result = await session.execute(
        select(Workflow)
        .where(Workflow.workspace_id == workspace_id)
        .order_by(Workflow.created_at.desc())
    )

    return list(result.scalars().all())

async def get_workflow(
    workflow_id: UUID,
    workspace_id: str,
    session: AsyncSession
) -> Workflow | None:
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    return result.scalar_one_or_none()


async def update_workflow(
    workflow_id: UUID,
    workspace_id: str,
    data: WorkflowUpdate,
    session: AsyncSession,
) -> Workflow | None:
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    workflow = result.scalar_one_or_none()

    if workflow is None:
        return None

    if data.name is not None:
        workflow.name = data.name

    if data.description is not None:
        workflow.description = data.description

    try:
        await session.commit()
        await session.refresh(workflow)
    except Exception:
        await session.rollback()
        raise

    return workflow