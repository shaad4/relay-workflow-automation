from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowUpdate
from app.schemas.workflow_node import WorkflowNodeCreate, WorkflowNodeResponse, WorkflowNodeUpdate
from app.schemas.workflow_version import WorkflowVersionResponse
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
    deleted = await delete_workflow(
        workflow_id=workflow_id,
        workspace_id=identity["workspace_id"],
        session=session,
    )

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