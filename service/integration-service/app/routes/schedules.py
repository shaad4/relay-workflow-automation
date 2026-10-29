from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.workflow_schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services.workflow_schedule_service import (
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
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


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleResponse,
)
async def update_workflow_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
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
        return await update_schedule(
            schedule_id=schedule_id,
            workspace_id=workspace_id,
            data=data,
            session=session,
        )


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workflow_schedule(
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
        await delete_schedule(
            schedule_id=schedule_id,
            workspace_id=workspace_id,
            session=session,
        )
