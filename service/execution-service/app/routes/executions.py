from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.repositories.execution import ExecutionRepository
from app.schemas.executions import (
    ExecutionListResponse,
    ExecutionDetailResponse,
)
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



@router.get(
    "/{execution_id}/",
    response_model=ExecutionDetailResponse,
)
async def get_execution_details(
    execution_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        workspace_id = UUID(identity["workspace_id"])

        repository = ExecutionRepository(session)
        service = ExecutionHistoryService(repository)

        execution = await service.get_execution_by_id(
            execution_id=execution_id,
            workspace_id=workspace_id,
        )

        if execution is None:
            raise HTTPException(
                status_code=404,
                detail="Execution not found",
            )

        return execution

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve execution details",
        ) from exc
