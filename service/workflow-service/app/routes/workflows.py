from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.models import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowResponse

router = APIRouter(prefix="/workflows", tags=["workflows"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    workflow = Workflow(
        workspace_id=identity["workspace_id"],
        name=data.name,
        description=data.description,
    )

    session.add(workflow)

    await session.commit()
    await session.refresh(workflow)

    return workflow