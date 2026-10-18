from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.models import Workflow, WorkflowVersion, WorkflowEdge, WorkflowNode
from app.schemas.workflow import WorkflowCreate, WorkflowUpdate
from app.schemas.node_configuration import (
    EmailConfig,
    RagSearchConfig,
    AIDecisionConfig,
    ConditionConfig,
    AIGenerateConfig,
    ManualTriggerConfig,
    ScheduledTriggerConfig,
)
from app.schemas.workflow_node import WorkflowNodeCreate, WorkflowNodeUpdate
from app.schemas.workflow_edge import WorkflowEdgeCreate, WorkflowEdgeUpdate
from app.grpc.integration_client import IntegrationGrpcClient

class ScheduleSynchronizationError(RuntimeError):
    """Publication committed, but schedule lifecycle synchronization failed."""


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

    try:
        session.add(workflow)
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

    if str(workflow.status).lower() not in {"draft", "inactive"}:
        raise ValueError(
            "Only draft or inactive workflows can be deleted. "
            "Deactivate an active workflow first."
        )

    try:
        workflow.published_version_id = None
        await session.flush()
        version_ids = select(WorkflowVersion.id).where(
            WorkflowVersion.workflow_id == workflow_id
        )
        await session.execute(
            delete(WorkflowNode).where(
                WorkflowNode.workflow_version_id.in_(version_ids)
            )
        )
        await session.execute(
            delete(WorkflowEdge).where(
                WorkflowEdge.workflow_version_id.in_(version_ids)
            )
        )
        await session.execute(
            delete(WorkflowVersion).where(
                WorkflowVersion.workflow_id == workflow_id
            )
        )
        await session.delete(workflow)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    client = IntegrationGrpcClient()
    try:
        await client.delete_workflow_schedule(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
        )
    finally:
        await client.close()

    return True


async def delete_workflow_version(
    workflow_id: UUID,
    version_number: int,
    workspace_id: str,
    session: AsyncSession,
) -> bool:
    workflow, version = await get_workflow_version(
        workflow_id=workflow_id,
        version_number=version_number,
        workspace_id=workspace_id,
        session=session,
    )
    if workflow is None or version is None:
        return False

    if (
        str(workflow.status).lower() in {"active", "published"}
        and workflow.published_version_id == version.id
    ):
        raise ValueError("Deactivate the workflow before deleting its active published version.")

    try:
        await session.execute(
            delete(WorkflowNode).where(WorkflowNode.workflow_version_id == version.id)
        )
        await session.execute(
            delete(WorkflowEdge).where(WorkflowEdge.workflow_version_id == version.id)
        )
        if workflow.published_version_id == version.id:
            workflow.published_version_id = None
            await session.flush()
        await session.delete(version)
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

    try:
        session.add(new_version)
        await session.flush()

        # Copy nodes from the latest version.
        node_result = await session.execute(
            select(WorkflowNode).where(
                WorkflowNode.workflow_version_id == latest_version.id,
            )
        )

        source_nodes = node_result.scalars().all()

        for node in source_nodes:
            configuration = node.configuration
            if node.node_type == "trigger.webhook":
                configuration = {"method": "POST", "setup_required": True}

            session.add(
                WorkflowNode(
                    workflow_version_id=new_version.id,
                    node_id=node.node_id,
                    node_type=node.node_type,
                    label=node.label,
                    position_x=node.position_x,
                    position_y=node.position_y,
                    configuration=configuration,
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

    duplicate_result = await session.execute(
        select(WorkflowNode.id).where(
            WorkflowNode.workflow_version_id == version.id,
            WorkflowNode.node_id == data.node_id,
        )
    )
    if duplicate_result.scalar_one_or_none() is not None:
        raise ValueError(f"Node ID '{data.node_id}' already exists in this version")

    node = WorkflowNode(
        workflow_version_id=version.id,
        node_id=data.node_id,
        node_type=data.node_type,
        label=data.label,
        position_x=data.position_x,
        position_y=data.position_y,
        configuration=data.configuration,
    )

    try:
        session.add(node)
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

    matching_nodes = node_result.scalars().all()
    if len(matching_nodes) > 1:
        raise ValueError(
            f"Node ID '{node_id}' is ambiguous because this version contains duplicates"
        )
    node = matching_nodes[0] if matching_nodes else None

    if node is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    new_node_id = update_data.get("node_id")
    if new_node_id is not None and new_node_id != node.node_id:
        duplicate_result = await session.execute(
            select(WorkflowNode.id).where(
                WorkflowNode.workflow_version_id == version.id,
                WorkflowNode.node_id == new_node_id,
                WorkflowNode.id != node.id,
            )
        )
        if duplicate_result.scalar_one_or_none() is not None:
            raise ValueError(f"Node ID '{new_node_id}' already exists in this version")

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

    nodes = node_result.scalars().all()

    if len(nodes) > 1:
        raise ValueError(
            f"Node ID '{node_id}' is ambiguous because this version contains duplicates"
        )

    node = nodes[0] if nodes else None

    if node is None:
        return None

    try:
        await session.delete(node)
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

    try:
        session.add(edge)
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

    try:
        await session.delete(edge)
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
    # 1. Validate workflow ownership
    workflow_result = await session.execute(
        select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
        )
    )

    workflow = workflow_result.scalar_one_or_none()

    if workflow is None:
        return None

    # 2. Retrieve workflow version
    version_result = await session.execute(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version == version_number,
        )
    )

    version = version_result.scalar_one_or_none()

    if version is None:
        return None

    # 3. Retrieve workflow nodes
    node_result = await session.execute(
        select(WorkflowNode).where(
            WorkflowNode.workflow_version_id == version.id,
        )
    )

    nodes = node_result.scalars().all()

    # 4. Retrieve workflow edges
    edge_result = await session.execute(
        select(WorkflowEdge).where(
            WorkflowEdge.workflow_version_id == version.id,
        )
    )

    edges = edge_result.scalars().all()

    errors = []
    warnings = []

    node_ids = {node.node_id for node in nodes}

    # 5. Validate that workflow contains nodes
    if not nodes:
        errors.append(
            {
                "code": "NO_NODES",
                "message": "Workflow must contain at least one node.",
            }
        )

    # 6. Check duplicate node IDs
    if len(node_ids) != len(nodes):
        errors.append(
            {
                "code": "DUPLICATE_NODE_ID",
                "message": "Workflow contains duplicate node IDs.",
            }
        )

    for node in nodes:
        if node.node_type != "action.email":
            continue
        try:
            EmailConfig.model_validate(node.configuration or {})
        except ValidationError as exc:
            for error in exc.errors():
                errors.append({
                    "code": "INVALID_EMAIL_CONFIGURATION",
                    "node_id": node.node_id,
                    "message": f"Send Email node '{node.node_id}': body_format - {error['msg']}",
                })

    # 7. Validate RAG Search configurations
    for node in nodes:
        if node.node_type != "ai.rag_search":
            continue

        try:
            RagSearchConfig.model_validate(
                node.configuration or {}
            )

        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(
                    str(part)
                    for part in error["loc"]
                ) or "configuration"

                errors.append(
                    {
                        "code": "INVALID_RAG_CONFIGURATION",
                        "node_id": node.node_id,
                        "message": (
                            f"RAG Search node '{node.node_id}': "
                            f"{field} - {error['msg']}"
                        ),
                    }
                )

    # 8. Validate AI Decision configurations
    for node in nodes:
        if node.node_type != "ai.decision":
            continue

        try:
            AIDecisionConfig.model_validate(
                node.configuration or {}
            )

        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(
                    str(part)
                    for part in error["loc"]
                ) or "configuration"

                errors.append(
                    {
                        "code": "INVALID_AI_DECISION_CONFIGURATION",
                        "node_id": node.node_id,
                        "message": (
                            f"AI Decision node '{node.node_id}': "
                            f"{field} - {error['msg']}"
                        ),
                    }
                )

    # 9. Validate Condition configurations
    for node in nodes:
        if node.node_type != "logic.condition":
            continue

        try:
            ConditionConfig.model_validate(
                node.configuration or {}
            )

        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(
                    str(part)
                    for part in error["loc"]
                ) or "configuration"

                errors.append(
                    {
                        "code": "INVALID_CONDITION_CONFIGURATION",
                        "node_id": node.node_id,
                        "message": (
                            f"Condition node '{node.node_id}': "
                            f"{field} - {error['msg']}"
                        ),
                    }
                )

    # 10. Validate AI Generate configurations
    for node in nodes:
        if node.node_type != "ai.generate":
            continue

        try:
            AIGenerateConfig.model_validate(
                node.configuration or {}
            )

        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(
                    str(part)
                    for part in error["loc"]
                ) or "configuration"

                errors.append(
                    {
                        "code": "INVALID_AI_GENERATE_CONFIGURATION",
                        "node_id": node.node_id,
                        "message": (
                            f"AI Generate node '{node.node_id}': "
                            f"{field} - {error['msg']}"
                        ),
                    }
                )

    # 11. Validate Manual Trigger configurations
    for node in nodes:
        if node.node_type != "trigger.manual":
            continue

        try:
            ManualTriggerConfig.model_validate(
                node.configuration or {}
            )
        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(
                    str(part) for part in error["loc"]
                ) or "configuration"
                errors.append(
                    {
                        "code": "INVALID_MANUAL_TRIGGER_CONFIGURATION",
                        "node_id": node.node_id,
                        "message": (
                            f"Manual Trigger node '{node.node_id}': "
                            f"{field} - {error['msg']}"
                        ),
                    }
                )

    # 12. Validate Scheduled Trigger configurations
    for node in nodes:
        if node.node_type != "trigger.schedule":
            continue

        try:
            ScheduledTriggerConfig.model_validate(
                node.configuration or {}
            )

        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(
                    str(part) for part in error["loc"]
                ) or "configuration"

                errors.append(
                    {
                        "code": "INVALID_SCHEDULE_CONFIGURATION",
                        "node_id": node.node_id,
                        "message": (
                            f"Scheduled Trigger node '{node.node_id}': "
                            f"{field} - {error['msg']}"
                        ),
                    }
                )

    # 13. Validate supported node types
    trigger_types = {
        "trigger.webhook",
        "trigger.manual",
        "trigger.schedule",
    }

    supported_types = trigger_types | {
        "action.http_request",
        "action.email",
        "action.refund",
        "human.approval",
        "ai.rag_search",
        "ai.decision",
        "ai.generate",
        "logic.condition",
    }

    # ai.generate is intentionally excluded until
    # its execution handler is implemented and tested.

    triggers = [
        node
        for node in nodes
        if node.node_type in trigger_types
    ]

    if len(triggers) != 1:
        errors.append(
            {
                "code": "INVALID_TRIGGER",
                "message": (
                    "Workflow must have exactly one supported trigger."
                ),
            }
        )

    for node in nodes:
        if node.node_type not in supported_types:
            errors.append(
                {
                    "code": "UNSUPPORTED_NODE_TYPE",
                    "node_id": node.node_id,
                    "message": (
                        f"Node '{node.node_id}' uses unsupported "
                        f"type '{node.node_type}'."
                    ),
                }
            )

    # 13. Validate edge references
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

    # 14. Build graph adjacency and indegree
    outgoing = {
        node_id: []
        for node_id in node_ids
    }

    indegree = {
        node_id: 0
        for node_id in node_ids
    }

    for edge in edges:
        if (
            edge.source_node_id in node_ids
            and edge.target_node_id in node_ids
        ):
            outgoing[edge.source_node_id].append(edge)
            indegree[edge.target_node_id] += 1

    # 15. Validate branching
    for node in nodes:
        branches = outgoing[node.node_id]

        if node.node_type == "human.approval":
            conditions = [
                edge.condition
                for edge in branches
            ]

            invalid = (
                any(
                    value not in {"approved", "rejected"}
                    for value in conditions
                )
                or len(set(conditions)) != len(conditions)
            )

        elif node.node_type == "logic.condition":
            conditions = [
                edge.condition
                for edge in branches
            ]

            invalid = (
                len(branches) == 0
                or any(
                    not isinstance(value, str)
                    or not value.strip()
                    or value != value.strip()
                    for value in conditions
                )
                or len(set(conditions)) != len(conditions)
            )

        else:
            invalid = len(branches) > 1

        if invalid:
            errors.append(
                {
                    "code": "INVALID_BRANCHING",
                    "node_id": node.node_id,
                    "message": (
                        f"Node '{node.node_id}' has invalid "
                        "or ambiguous outgoing branches."
                    ),
                }
            )

    # 16. Detect workflow cycles using Kahn's algorithm
    pending = [
        node_id
        for node_id, count in indegree.items()
        if count == 0
    ]

    visited = set()

    while pending:
        node_id = pending.pop()

        visited.add(node_id)

        for edge in outgoing[node_id]:
            indegree[edge.target_node_id] -= 1

            if indegree[edge.target_node_id] == 0:
                pending.append(
                    edge.target_node_id
                )

    if len(visited) != len(node_ids):
        errors.append(
            {
                "code": "WORKFLOW_CYCLE",
                "message": "Workflow must not contain cycles.",
            }
        )

    # 17. Verify all nodes are reachable from trigger
    if len(triggers) == 1:
        reachable = set()
        pending = [triggers[0].node_id]

        while pending:
            node_id = pending.pop()

            if node_id in reachable:
                continue

            reachable.add(node_id)

            pending.extend(
                edge.target_node_id
                for edge in outgoing[node_id]
            )

        if reachable != node_ids:
            errors.append(
                {
                    "code": "DISCONNECTED_NODES",
                    "message": (
                        "Every node must be reachable "
                        "from the trigger."
                    ),
                }
            )

    # 18. Return validation result
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


async def _published_version_has_schedule_trigger(
    version_id: UUID,
    session: AsyncSession,
) -> bool:
    result = await session.execute(
        select(WorkflowNode.id).where(
            WorkflowNode.workflow_version_id == version_id,
            WorkflowNode.node_type == "trigger.schedule",
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


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

    already_published = (
        version.status == "published"
        and workflow.published_version_id == version.id
        and workflow.status == "active"
    )
    if version.status != "draft" and not already_published:
        raise ValueError("Only draft versions can be published")

    if not already_published:
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

    has_schedule_trigger = await _published_version_has_schedule_trigger(
        version.id, session
    )

    if not already_published:
        version.status = "published"
        workflow.status = "active"
        workflow.published_version_id = version.id
        try:
            await session.commit()
            await session.refresh(version)
        except Exception:
            await session.rollback()
            raise

    client = IntegrationGrpcClient()
    try:
        await client.sync_workflow_schedule(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
            workflow_version_id=version.id,
            has_schedule_trigger=has_schedule_trigger,
            workflow_active=True,
        )
    except Exception as exc:
        raise ScheduleSynchronizationError(
            "Workflow was published, but schedule synchronization could not be confirmed."
        ) from exc
    finally:
        await client.close()

    return {
        "id": version.id,
        "workflow_id": workflow_id,
        "version": version.version,
        "status": version.status,
    }


async def deactivate_workflow(
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
    if workflow.published_version_id is None:
        raise ValueError("Workflow has no published version")
    if workflow.status == "inactive":
        raise ValueError("Workflow is already inactive")

    # Suspend first so a failed gRPC request cannot leave an active schedule
    # after the workflow is marked inactive.
    client = IntegrationGrpcClient()
    try:
        await client.suspend_workflow_schedule(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
        )
    finally:
        await client.close()

    workflow.status = "inactive"
    try:
        await session.commit()
        await session.refresh(workflow)
    except Exception:
        await session.rollback()
        raise
    return workflow


async def activate_workflow(
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
    if workflow.published_version_id is None:
        raise ValueError("Workflow has no published version")
    if workflow.status == "active":
        raise ValueError("Workflow is already active")

    has_schedule_trigger = await _published_version_has_schedule_trigger(
        workflow.published_version_id, session
    )

    workflow.status = "active"
    try:
        await session.commit()
        await session.refresh(workflow)
    except Exception:
        await session.rollback()
        raise

    client = IntegrationGrpcClient()
    try:
        await client.sync_workflow_schedule(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
            workflow_version_id=workflow.published_version_id,
            has_schedule_trigger=has_schedule_trigger,
            workflow_active=True,
        )
    finally:
        await client.close()

    return workflow
