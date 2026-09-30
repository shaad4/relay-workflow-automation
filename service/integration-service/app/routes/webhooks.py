import grpc
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.webhook import WebhookCreate, WebhookResponse
from app.services.webhook_service import create_webhook


router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook_route(
    data: WebhookCreate,
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
        return await create_webhook(
            data=data,
            workspace_id=workspace_id,
            session=session,
        )
    except grpc.aio.AioRpcError as exc:
        if exc.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow or workflow version not found",
            ) from exc

        if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Workflow Service request timed out",
            ) from exc

        if exc.code() == grpc.StatusCode.UNAVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow Service is unavailable",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to validate workflow",
        ) from exc