from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workflow, WorkflowVersion, WorkflowEdge, WorkflowNode
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.workflow_node import WorkflowNodeCreate, WorkflowNodeUpdate
from app.schemas.workflow_edge import WorkflowEdgeCreate, WorkflowEdgeUpdate

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


async def list_workflow_nodes(
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

    node_result = await session.execute(
        select(WorkflowNode)
        .where(
            WorkflowNode.workflow_version_id == version.id,
        )
        .order_by(WorkflowNode.created_at)
    )

    return node_result.scalars().all()


async def update_workflow_node(
    workflow_id: UUID,
    version_number: int,
    node_id: str,
    workspace_id: str,
    data: WorkflowNodeUpdate,
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

    node_result = await session.execute(
        select(WorkflowNode).where(
            WorkflowNode.workflow_version_id == version.id,
            WorkflowNode.node_id == node_id,
        )
    )

    node = node_result.scalar_one_or_none()

    if node is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(node, field, value)

    try:
        await session.commit()
        await session.refresh(node)
    except Exception:
        await session.rollback()
        raise

    return node

async def delete_workflow_node(
    workflow_id: UUID,
    version_number: int,
    node_id: str,
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

    node_result = await session.execute(
        select(WorkflowNode).where(
            WorkflowNode.workflow_version_id == version.id,
            WorkflowNode.node_id == node_id,
        )
    )

    node = node_result.scalar_one_or_none()

    if node is None:
        return None

    await session.delete(node)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return True


async def create_workflow_edge(
    workflow_id: UUID,
    version_number: int,
    workspace_id: str,
    data: WorkflowEdgeCreate,
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

    source_node_result = await session.execute(
        select(WorkflowNode).where(
            WorkflowNode.workflow_version_id == version.id,
            WorkflowNode.node_id == data.source_node_id,
        )
    )

    source_node = source_node_result.scalar_one_or_none()

    if source_node is None:
        raise ValueError("Source node not found")

    target_node_result = await session.execute(
        select(WorkflowNode).where(
            WorkflowNode.workflow_version_id == version.id,
            WorkflowNode.node_id == data.target_node_id,
        )
    )

    target_node = target_node_result.scalar_one_or_none()

    if target_node is None:
        raise ValueError("Target node not found")

    edge = WorkflowEdge(
        workflow_version_id=version.id,
        source_node_id=data.source_node_id,
        target_node_id=data.target_node_id,
        condition=data.condition,
    )

    session.add(edge)

    try:
        await session.commit()
        await session.refresh(edge)
    except Exception:
        await session.rollback()
        raise

    return edge


async def list_workflow_edges(
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

    edge_result = await session.execute(
        select(WorkflowEdge)
        .where(
            WorkflowEdge.workflow_version_id == version.id,
        )
        .order_by(WorkflowEdge.created_at)
    )

    return edge_result.scalars().all()


async def update_workflow_edge(
    workflow_id: UUID,
    version_number: int,
    edge_id: UUID,
    workspace_id: str,
    data: WorkflowEdgeUpdate,
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

    edge_result = await session.execute(
        select(WorkflowEdge).where(
            WorkflowEdge.id == edge_id,
            WorkflowEdge.workflow_version_id == version.id,
        )
    )

    edge = edge_result.scalar_one_or_none()

    if edge is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    if "source_node_id" in update_data:
        source_result = await session.execute(
            select(WorkflowNode).where(
                WorkflowNode.workflow_version_id == version.id,
                WorkflowNode.node_id == update_data["source_node_id"],
            )
        )

        if source_result.scalar_one_or_none() is None:
            raise ValueError("Source node not found")

    if "target_node_id" in update_data:
        target_result = await session.execute(
            select(WorkflowNode).where(
                WorkflowNode.workflow_version_id == version.id,
                WorkflowNode.node_id == update_data["target_node_id"],
            )
        )

        if target_result.scalar_one_or_none() is None:
            raise ValueError("Target node not found")

    for field, value in update_data.items():
        setattr(edge, field, value)

    try:
        await session.commit()
        await session.refresh(edge)
    except Exception:
        await session.rollback()
        raise

    return edge


async def delete_workflow_edge(
    workflow_id: UUID,
    version_number: int,
    edge_id: UUID,
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

    edge_result = await session.execute(
        select(WorkflowEdge).where(
            WorkflowEdge.id == edge_id,
            WorkflowEdge.workflow_version_id == version.id,
        )
    )

    edge = edge_result.scalar_one_or_none()

    if edge is None:
        return None

    await session.delete(edge)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return True


async def validate_workflow(
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

    node_result = await session.execute(
        select(WorkflowNode).where(
            WorkflowNode.workflow_version_id == version.id,
        )
    )

    nodes = node_result.scalars().all()

    edge_result = await session.execute(
        select(WorkflowEdge).where(
            WorkflowEdge.workflow_version_id == version.id,
        )
    )

    edges = edge_result.scalars().all()

    errors = []
    warnings = []

    node_ids = {node.node_id for node in nodes}

    # Check that the workflow has at least one node.
    if not nodes:
        errors.append(
            {
                "code": "NO_NODES",
                "message": "Workflow must contain at least one node.",
            }
        )

    # Check for duplicate node IDs.
    if len(node_ids) != len(nodes):
        errors.append(
            {
                "code": "DUPLICATE_NODE_ID",
                "message": "Workflow contains duplicate node IDs.",
            }
        )

    # Check that every edge references existing nodes.
    for edge in edges:
        if edge.source_node_id not in node_ids:
            errors.append(
                {
                    "code": "INVALID_EDGE_SOURCE",
                    "message": (
                        f"Edge references missing source node "
                        f"'{edge.source_node_id}'."
                    ),
                }
            )

        if edge.target_node_id not in node_ids:
            errors.append(
                {
                    "code": "INVALID_EDGE_TARGET",
                    "message": (
                        f"Edge references missing target node "
                        f"'{edge.target_node_id}'."
                    ),
                }
            )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


async def publish_workflow(
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
        raise ValueError("Only draft versions can be published")

    validation_result = await validate_workflow(
        workflow_id=workflow_id,
        version_number=version_number,
        workspace_id=workspace_id,
        session=session,
    )

    if validation_result is None:
        return None

    if not validation_result["valid"]:
        raise ValueError("Workflow validation failed")

    version.status = "published"

    workflow.status = "published"
    workflow.published_version_id = version.id

    try:
        await session.commit()
        await session.refresh(version)
    except Exception:
        await session.rollback()
        raise

    return {
        "id": version.id,
        "workflow_id": workflow_id,
        "version": version.version,
        "status": version.status,
    }