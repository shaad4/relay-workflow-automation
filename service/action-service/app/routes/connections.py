import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_identity, get_db
from app.schemas.connection import ConnectionCreate, ConnectionResponse
from app.services.connection_service import create_connection


router = APIRouter(
    prefix="/connections",
    tags=["connections"],
)


@router.post(
    "/",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection_route(
    data: ConnectionCreate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        workspace_id = uuid.UUID(identity["workspace_id"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workspace identity",
        )

    try:
        connection = await create_connection(
            data=data,
            workspace_id=workspace_id,
            session=session,
        )

        return connection

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create connection",
        ) from exc