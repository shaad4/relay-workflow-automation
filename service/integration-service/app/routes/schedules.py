from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.workflow_schedule import (
    ScheduleCreate,
    ScheduleResponse,
)
from app.services.workflow_schedule_service import (
    create_schedule,
    list_schedules,
    get_schedule,
)

router = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
)


@router.post(
    "/",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_schedule(
    data: ScheduleCreate,
    identity: dict = Depends(get_current_identity),
):
    try:
        workspace_id = UUID(identity["workspace_id"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid workspace identity",
        )

    async with AsyncSessionLocal() as session:
        return await create_schedule(
            data=data,
            workspace_id=workspace_id,
            session=session,
        )

@router.get(
    "/",
    response_model=list[ScheduleResponse],
)
async def list_workflow_schedules(
    identity: dict = Depends(get_current_identity),
):
    try:
        workspace_id = UUID(identity["workspace_id"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid workspace identity",
        )

    async with AsyncSessionLocal() as session:
        return await list_schedules(
            workspace_id=workspace_id,
            session=session,
        )


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse,
)
async def get_workflow_schedule(
    schedule_id: UUID,
    identity: dict = Depends(get_current_identity),
):
    try:
        workspace_id = UUID(identity["workspace_id"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid workspace identity",
        )

    async with AsyncSessionLocal() as session:
        return await get_schedule(
            schedule_id=schedule_id,
            workspace_id=workspace_id,
            session=session,
        )