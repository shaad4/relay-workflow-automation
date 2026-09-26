from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workflow, WorkflowVersion, WorkflowEdge, WorkflowNode
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.workflow_node import WorkflowNodeCreate


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

    try:
        await session.flush()

        version = WorkflowVersion(
            workflow_id=workflow.id,
            version=1,
            status="draft",
            description="Initial version"
        )

        session.add(version)

        await session.commit()
        await session.refresh(workflow)
    except Exception:
        await session.rollback()
        raise

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


async def delete_workflow(
    workflow_id: UUID,
    workspace_id: str,
    session: AsyncSession,
) -> bool:
    result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    workflow = result.scalar_one_or_none()

    if workflow is None:
        return False

    try:
        await session.delete(workflow)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return True

async def list_workflow_versions(
    workflow_id: UUID,
    workspace_id: str,
    session: AsyncSession,
):
    workflow_result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    workflow = workflow_result.scalar_one_or_none()

    if workflow is None:
        return None

    result = await session.execute(
        select(WorkflowVersion)
        .where(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version.desc())
    )

    return list(result.scalars().all())

async def get_workflow_version(
    workflow_id: UUID,
    version_number: int,
    workspace_id: str,
    session: AsyncSession,
):
    workflow_result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    workflow = workflow_result.scalar_one_or_none()

    if workflow is None:
        return None, None

    result = await session.execute(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == version_number,
        )
    )

    version = result.scalar_one_or_none()

    return workflow, version


async def create_draft_version(
    workflow_id: UUID,
    workspace_id: str,
    session: AsyncSession,
):
    # Verify the workflow belongs to the current workspace.
    workflow_result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    workflow = workflow_result.scalar_one_or_none()

    if workflow is None:
        return None

    # Get the latest version.
    version_result = await session.execute(
        select(WorkflowVersion)
        .where(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version.desc())
    )

    latest_version = version_result.scalars().first()

    if latest_version is None:
        return None

    # Create the next version as a draft.
    new_version = WorkflowVersion(
        workflow_id=workflow_id,
        version=latest_version.version + 1,
        status="draft",
        description=latest_version.description,
    )

    session.add(new_version)

    try:
        await session.flush()

        # Copy nodes from the latest version.
        node_result = await session.execute(
            select(WorkflowNode).where(
                WorkflowNode.workflow_version_id == latest_version.id,
            )
        )

        source_nodes = node_result.scalars().all()

        for node in source_nodes:
            session.add(
                WorkflowNode(
                    workflow_version_id=new_version.id,
                    node_id=node.node_id,
                    node_type=node.node_type,
                    label=node.label,
                    position_x=node.position_x,
                    position_y=node.position_y,
                    configuration=node.configuration,
                )
            )

        # Copy edges from the latest version.
        edge_result = await session.execute(
            select(WorkflowEdge).where(
                WorkflowEdge.workflow_version_id == latest_version.id,
            )
        )

        source_edges = edge_result.scalars().all()

        for edge in source_edges:
            session.add(
                WorkflowEdge(
                    workflow_version_id=new_version.id,
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    condition=edge.condition,
                )
            )

        await session.commit()
        await session.refresh(new_version)

    except Exception:
        await session.rollback()
        raise

    return new_version


async def create_workflow_node(
    workflow_id: UUID,
    version_number: int,
    workspace_id: str,
    data: WorkflowNodeCreate,
    session: AsyncSession,
):
    workflow_result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    workflow = workflow_result.scalar_one_or_none()

    if workflow is None:
        return None

    version_result = await session.execute(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == version_number,
        )
    )

    version = version_result.scalar_one_or_none()

    if version is None:
        return None

    if version.status != "draft":
        raise ValueError("Only draft versions can be modified")

    node = WorkflowNode(
        workflow_version_id=version.id,
        node_id=data.node_id,
        node_type=data.node_type,
        label=data.label,
        position_x=data.position_x,
        position_y=data.position_y,
        configuration=data.configuration,
    )

    session.add(node)

    try:
        await session.commit()
        await session.refresh(node)
    except Exception:
        await session.rollback()
        raise

    return node