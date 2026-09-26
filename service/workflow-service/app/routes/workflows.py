from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.workflow import WorkflowCreate, WorkflowResponse
from app.services.workflow_service import (
    create_workflow,
    list_workflows,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=WorkflowResponse, status_code=201)
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