import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_identity, get_db
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate, ConnectionTestResponse
from app.services.connection_service import(
    create_connection,
    get_connections,
    get_connection,
    update_connection,
    delete_connection,
    test_connection,
) 


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


@router.get(
    "/",
    response_model=list[ConnectionResponse],
)
async def get_connections_route(
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
        connections = await get_connections(
            workspace_id=workspace_id,
            session=session,
        )

        return connections

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch connections",
        ) from exc


@router.get(
    "/{connection_id}/",
    response_model=ConnectionResponse,
)
async def get_connection_route(
    connection_id: uuid.UUID,
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
        connection = await get_connection(
            connection_id=connection_id,
            workspace_id=workspace_id,
            session=session,
        )

        if connection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found",
            )

        return connection

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch connection",
        ) from exc


@router.patch(
    "/{connection_id}/",
    response_model=ConnectionResponse,
)
async def update_connection_route(
    connection_id: uuid.UUID,
    data: ConnectionUpdate,
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
        connection = await update_connection(
            connection_id=connection_id,
            workspace_id=workspace_id,
            data=data,
            session=session,
        )

        if connection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found",
            )

        return connection

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update connection",
        ) from exc



@router.delete(
    "/{connection_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_connection_route(
    connection_id: uuid.UUID,
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
        deleted = await delete_connection(
            connection_id=connection_id,
            workspace_id=workspace_id,
            session=session,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found",
            )

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete connection",
        ) from exc


@router.post(
    "/{connection_id}/test/",
    response_model=ConnectionTestResponse,
)
async def test_connection_route(
    connection_id: uuid.UUID,
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
        return await test_connection(
            connection_id=connection_id,
            workspace_id=workspace_id,
            session=session,
        )

    except ValueError as exc:
        if str(exc) == "Connection not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test connection",
        ) from exc