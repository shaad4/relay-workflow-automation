from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.ai_provider_connection import (
    AIProviderConnectionCreate,
    AIProviderConnectionUpdate,
    AIProviderConnectionResponse,
)
from app.services.ai_provider_connection import (
    AIProviderConnectionService,
)


router = APIRouter(
    prefix="/ai/connections",
    tags=["AI Provider Connections"],
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post(
    "/",
    response_model=AIProviderConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_connection(
    data: AIProviderConnectionCreate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    service = AIProviderConnectionService(session)

    try:
        connection = await service.create(
            workspace_id=UUID(identity["workspace_id"]),
            name=data.name,
            provider=data.provider,
            api_key=data.api_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return AIProviderConnectionResponse.model_validate(
        connection
    )


@router.get(
    "/",
    response_model=list[AIProviderConnectionResponse],
)
async def list_ai_connections(
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    service = AIProviderConnectionService(session)

    connections = await service.list(
        workspace_id=UUID(identity["workspace_id"]),
    )

    return [
        AIProviderConnectionResponse.model_validate(
            connection
        )
        for connection in connections
    ]


@router.get(
    "/{connection_id}/",
    response_model=AIProviderConnectionResponse,
)
async def get_ai_connection(
    connection_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    service = AIProviderConnectionService(session)

    connection = await service.get(
        connection_id=connection_id,
        workspace_id=UUID(identity["workspace_id"]),
    )

    if connection is None:
        raise HTTPException(
            status_code=404,
            detail="AI connection not found",
        )

    return AIProviderConnectionResponse.model_validate(
        connection
    )


@router.patch(
    "/{connection_id}/",
    response_model=AIProviderConnectionResponse,
)
async def update_ai_connection(
    connection_id: UUID,
    data: AIProviderConnectionUpdate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    service = AIProviderConnectionService(session)

    try:
        connection = await service.update(
            connection_id=connection_id,
            workspace_id=UUID(identity["workspace_id"]),
            **data.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if connection is None:
        raise HTTPException(
            status_code=404,
            detail="AI connection not found",
        )

    return AIProviderConnectionResponse.model_validate(
        connection
    )


@router.delete(
    "/{connection_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ai_connection(
    connection_id: UUID,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    service = AIProviderConnectionService(session)

    deleted = await service.delete(
        connection_id=connection_id,
        workspace_id=UUID(identity["workspace_id"]),
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="AI connection not found",
        )

    return None
