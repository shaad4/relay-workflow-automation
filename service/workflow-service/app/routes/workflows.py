from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowUpdate, WorkflowValidationResponse, WorkflowPublishResponse, WorkflowStatusResponse
from app.schemas.workflow_node import WorkflowNodeCreate, WorkflowNodeResponse, WorkflowNodeUpdate
from app.schemas.workflow_version import WorkflowVersionResponse
from app.schemas.workflow_edge import WorkflowEdgeResponse, WorkflowEdgeCreate, WorkflowEdgeUpdate
from app.services.workflow_service import (
    create_workflow,
    list_workflows,
    get_workflow,
    update_workflow,
    delete_workflow,
    list_workflow_versions,
    get_workflow_version,
    create_draft_version,
    create_workflow_node,
    list_workflow_nodes,
    update_workflow_node,
    delete_workflow_node,
    create_workflow_edge,
    list_workflow_edges,
    update_workflow_edge,
    delete_workflow_edge,
    validate_workflow,
    publish_workflow,
    activate_workflow,
    deactivate_workflow,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/", response_model=WorkflowResponse, status_code=201)
async def create_workflow_route(
    data: WorkflowCreate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    return await create_workflow(
        data=data,
        workspace_id=identity["workspace_id"],
        session=session,
    )


@router.get("/", response_model=list[WorkflowResponse])
async def list_workflows_route(
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    return await list_workflows(
        workspace_id=identity["workspace_id"],
        session=session,
    )

@router.get("/{workflow_id}/", response_model=WorkflowResponse)
async def get_workflow_route(
    workflow_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workflow = await get_workflow(
        workflow_id=workflow_id,
        workspace_id=identity["workspace_id"],
        session=session,
    )

    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return workflow


@router.patch("/{workflow_id}/", response_model=WorkflowResponse)
async def update_workflow_route(
    workflow_id: UUID,
    data: WorkflowUpdate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workflow = await update_workflow(
        workflow_id=workflow_id,
        workspace_id=identity["workspace_id"],
        data=data,
        session=session,
    )

    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return workflow


@router.delete("/{workflow_id}/", status_code=204)
async def delete_workflow_route(
    workflow_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        deleted = await delete_workflow(
            workflow_id=workflow_id,
            workspace_id=identity["workspace_id"],
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return None


@router.get(
    "/{workflow_id}/versions/",
    response_model=list[WorkflowVersionResponse],
)
async def list_workflow_versions_route(
    workflow_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    versions = await list_workflow_versions(
        workflow_id=workflow_id,
        workspace_id=identity["workspace_id"],
        session=session,
    )

    if versions is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return versions

@router.get(
    "/{workflow_id}/versions/{version_number}/",
    response_model=WorkflowVersionResponse,
)
async def get_workflow_version_route(
    workflow_id: UUID,
    version_number: int,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workflow, version = await get_workflow_version(
        workflow_id=workflow_id,
        version_number=version_number,
        workspace_id=identity["workspace_id"],
        session=session,
    )

    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    if version is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow version not found",
        )

    return version

@router.post(
    "/{workflow_id}/draft/",
    response_model=WorkflowVersionResponse,
    status_code=201,
)
async def create_draft_version_route(
    workflow_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    version = await create_draft_version(
        workflow_id=workflow_id,
        workspace_id=identity["workspace_id"],
        session=session,
    )

    if version is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return version

@router.post(
    "/{workflow_id}/versions/{version_number}/nodes/",
    response_model=WorkflowNodeResponse,
    status_code=201,
)
async def create_workflow_node_route(
    workflow_id: UUID,
    version_number: int,
    data: WorkflowNodeCreate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        node = await create_workflow_node(
            workflow_id=workflow_id,
            version_number=version_number,
            workspace_id=identity["workspace_id"],
            data=data,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        # The database uniqueness constraint also protects against concurrent
        # requests racing past the service-level duplicate check.
        raise HTTPException(
            status_code=409,
            detail="A node with this ID already exists in this version",
        ) from exc

    if node is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow or version not found",
        )

    return node


@router.get(
    "/{workflow_id}/versions/{version_number}/nodes/",
    response_model=list[WorkflowNodeResponse],
)
async def list_workflow_nodes_route(
    workflow_id: UUID,
    version_number: int,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    nodes = await list_workflow_nodes(
        workflow_id=workflow_id,
        version_number=version_number,
        workspace_id=identity["workspace_id"],
        session=session,
    )

    if nodes is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow or version not found",
        )

    return nodes

@router.patch(
    "/{workflow_id}/versions/{version_number}/nodes/{node_id}/",
    response_model=WorkflowNodeResponse,
)
async def update_workflow_node_route(
    workflow_id: UUID,
    version_number: int,
    node_id: str,
    data: WorkflowNodeUpdate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        node = await update_workflow_node(
            workflow_id=workflow_id,
            version_number=version_number,
            node_id=node_id,
            workspace_id=identity["workspace_id"],
            data=data,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if node is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow, version, or node not found",
        )

    return node


@router.delete(
    "/{workflow_id}/versions/{version_number}/nodes/{node_id}/",
    status_code=204,
)
async def delete_workflow_node_route(
    workflow_id: UUID,
    version_number: int,
    node_id: str,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        deleted = await delete_workflow_node(
            workflow_id=workflow_id,
            version_number=version_number,
            node_id=node_id,
            workspace_id=identity["workspace_id"],
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow, version, or node not found",
        )

@router.post(
    "/{workflow_id}/versions/{version_number}/edges/",
    response_model=WorkflowEdgeResponse,
    status_code=201,
)
async def create_workflow_edge_route(
    workflow_id: UUID,
    version_number: int,
    data: WorkflowEdgeCreate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        edge = await create_workflow_edge(
            workflow_id=workflow_id,
            version_number=version_number,
            workspace_id=identity["workspace_id"],
            data=data,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if edge is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow or version not found",
        )

    return edge


@router.get(
    "/{workflow_id}/versions/{version_number}/edges/",
    response_model=list[WorkflowEdgeResponse],
)
async def list_workflow_edges_route(
    workflow_id: UUID,
    version_number: int,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    edges = await list_workflow_edges(
        workflow_id=workflow_id,
        version_number=version_number,
        workspace_id=identity["workspace_id"],
        session=session,
    )

    if edges is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow or version not found",
        )

    return edges


@router.patch(
    "/{workflow_id}/versions/{version_number}/edges/{edge_id}/",
    response_model=WorkflowEdgeResponse,
)
async def update_workflow_edge_route(
    workflow_id: UUID,
    version_number: int,
    edge_id: UUID,
    data: WorkflowEdgeUpdate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        edge = await update_workflow_edge(
            workflow_id=workflow_id,
            version_number=version_number,
            edge_id=edge_id,
            workspace_id=identity["workspace_id"],
            data=data,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if edge is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow, version, or edge not found",
        )

    return edge



@router.delete(
    "/{workflow_id}/versions/{version_number}/edges/{edge_id}/",
    status_code=204,
)
async def delete_workflow_edge_route(
    workflow_id: UUID,
    version_number: int,
    edge_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        deleted = await delete_workflow_edge(
            workflow_id=workflow_id,
            version_number=version_number,
            edge_id=edge_id,
            workspace_id=identity["workspace_id"],
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow, version, or edge not found",
        )

@router.post(
    "/{workflow_id}/versions/{version_number}/validate/",
    response_model=WorkflowValidationResponse,
)
async def validate_workflow_route(
    workflow_id: UUID,
    version_number: int,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    result = await validate_workflow(
        workflow_id=workflow_id,
        version_number=version_number,
        workspace_id=identity["workspace_id"],
        session=session,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow or version not found",
        )

    return result


@router.post(
    "/{workflow_id}/versions/{version_number}/publish/",
    response_model=WorkflowPublishResponse,
)
async def publish_workflow_version_route(
    workflow_id: UUID,
    version_number: int,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await publish_workflow(
            workflow_id=workflow_id,
            version_number=version_number,
            workspace_id=identity["workspace_id"],
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow or version not found",
        )

    return result


@router.post(
    "/{workflow_id}/deactivate/",
    response_model=WorkflowStatusResponse,
)
async def deactivate_workflow_route(
    workflow_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await deactivate_workflow(
            workflow_id=workflow_id,
            workspace_id=identity["workspace_id"],
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return {
        "id": result.id,
        "status": result.status,
        "published_version_id": result.published_version_id,
    }


@router.post(
    "/{workflow_id}/activate/",
    response_model=WorkflowStatusResponse,
)
async def activate_workflow_route(
    workflow_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await activate_workflow(
            workflow_id=workflow_id,
            workspace_id=identity["workspace_id"],
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
        )

    return {
        "id": result.id,
        "status": result.status,
        "published_version_id": result.published_version_id,
    }
