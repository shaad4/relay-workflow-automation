from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.repositories.execution import ExecutionRepository
from app.schemas.executions import ExecutionListResponse
from app.services.execution_history import ExecutionHistoryService


router = APIRouter(
    prefix="/executions",
    tags=["Execution History"],
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(default=None),
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        workspace_id = UUID(identity["workspace_id"])

        repository = ExecutionRepository(session)
        service = ExecutionHistoryService(repository)

        return await service.list_executions(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            status=status,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve execution history",
        ) from exc
