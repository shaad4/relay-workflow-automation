import grpc
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.dependencies import get_current_identity
from app.schemas.webhook import WebhookCreate, WebhookResponse, WebhookUpdate, WebhookCreateResponse
from app.services.webhook_service import (
    create_webhook,
    list_webhooks,
    get_webhook,
    update_webhook,
    delete_webhook,
    regenerate_webhook_token,
)


router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post(
    "/",
    response_model=WebhookCreateResponse,
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
        webhook, secret = await create_webhook(
            data=data,
            workspace_id=workspace_id,
            session=session,
        )

        response = WebhookCreateResponse.model_validate(webhook)
        response.secret = secret

        return response

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


@router.get(
    "/",
    response_model=list[WebhookResponse],
)
async def list_webhooks_route(
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

    return await list_webhooks(
        workspace_id=workspace_id,
        session=session,
    )


@router.get(
    "/{webhook_id}/",
    response_model=WebhookResponse,
)
async def get_webhook_route(
    webhook_id: uuid.UUID,
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

    webhook = await get_webhook(
        webhook_id=webhook_id,
        workspace_id=workspace_id,
        session=session,
    )

    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return webhook


@router.patch("/{webhook_id}/", response_model=WebhookResponse)
async def update_webhook_endpoint(
    webhook_id: str,
    data: WebhookUpdate,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        webhook_uuid = uuid.UUID(webhook_id)
        workspace_id = uuid.UUID(identity["workspace_id"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook ID",
        )

    webhook = await update_webhook(
        webhook_id=webhook_uuid,
        data=data,
        workspace_id=workspace_id,
        session=session,
    )

    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return webhook


@router.delete("/{webhook_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_endpoint(
    webhook_id: str,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        webhook_uuid = uuid.UUID(webhook_id)
        workspace_id = uuid.UUID(identity["workspace_id"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook ID",
        )

    deleted = await delete_webhook(
        webhook_id=webhook_uuid,
        workspace_id=workspace_id,
        session=session,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{webhook_id}/regenerate-token/",
    response_model=WebhookResponse,
)
async def regenerate_webhook_token_endpoint(
    webhook_id: str,
    identity: dict = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
):
    try:
        webhook_uuid = uuid.UUID(webhook_id)
        workspace_id = uuid.UUID(identity["workspace_id"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook ID",
        )

    webhook = await regenerate_webhook_token(
        webhook_id=webhook_uuid,
        workspace_id=workspace_id,
        session=session,
    )

    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return webhook


