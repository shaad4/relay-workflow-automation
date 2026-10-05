from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import grpc

from .webhooks import get_db
from app.services.webhook_service import (
    InactiveWorkflowError,
    UnpublishedWorkflowVersionError,
    WorkflowVersionNotFoundError,
    get_webhook_by_public_token,
    validate_workflow_version,
    verify_webhook_secret,
)
from app.services.webhook_test_sessions import publish_result, publish_session_result
from app.kafka.producer import publish_workflow_triggered
from app.schemas.events import WorkflowTriggeredEvent


router = APIRouter(
    prefix="/hooks",
    tags=["public-webhooks"],
)


@router.post("/{public_token}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(
    public_token: str,
    request: Request,
    x_relay_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    # 1. Find webhook using the public token
    webhook = await get_webhook_by_public_token(
        public_token=public_token,
        session=session,
    )

    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # 2. Check whether webhook is active
    if not webhook.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook is inactive",
        )

    # 3. Validate secret when authentication is enabled
    if webhook.authentication_type == "secret":

        if not x_relay_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook secret is required",
            )

        if not webhook.secret_hash:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook authentication is not configured correctly",
            )

        if not verify_webhook_secret(
            secret=x_relay_secret,
            secret_hash=webhook.secret_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret",
            )

    # Validate legacy webhook rows as well as newly configured ones. This
    # happens before producing Kafka events so a draft version cannot start
    # an execution.
    try:
        await validate_workflow_version(
            workflow_id=webhook.workflow_id,
            workflow_version_id=webhook.workflow_version_id,
            workspace_id=webhook.workspace_id,
        )
    except UnpublishedWorkflowVersionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InactiveWorkflowError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkflowVersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except grpc.aio.AioRpcError as exc:
        if exc.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow or workflow version not found") from exc
        if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Workflow Service request timed out") from exc
        if exc.code() == grpc.StatusCode.UNAVAILABLE:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Workflow Service is unavailable") from exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to validate workflow") from exc

    # 4. Read the incoming webhook payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must be valid JSON",
        )

    # 5. Create workflow.triggered event
    event = WorkflowTriggeredEvent(
        event_id=uuid4(),
        workspace_id=webhook.workspace_id,
        workflow_id=webhook.workflow_id,
        workflow_version_id=webhook.workflow_version_id,
        webhook_id=webhook.id,
        payload=payload,
    )

    # 6. Publish event to Kafka
    await publish_workflow_triggered(event)

    # 7. Webhook accepted
    return {
        "message": "Webhook accepted",
        "webhook_id": str(webhook.id),
        "event_id": str(event.event_id),
    }


@router.post("/{public_token}/test")
async def test_webhook(
    public_token: str,
    request: Request,
    x_relay_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    test_session_id = request.query_params.get("relay_test_session")
    # 1. Find webhook using the public token
    webhook = await get_webhook_by_public_token(
        public_token=public_token,
        session=session,
    )

    if webhook is None:
        if test_session_id:
            await publish_session_result(
                test_session_id,
                "failed",
                {"status_code": 404, "detail": "Webhook not found"},
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # 2. Check whether webhook is active
    if not webhook.is_active:
        if test_session_id:
            await publish_result(test_session_id, str(webhook.id), "failed", {"status_code": 403, "detail": "Webhook is inactive"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook is inactive",
        )

    # 3. Validate secret when authentication is enabled
    if webhook.authentication_type == "secret":

        if not x_relay_secret:
            if test_session_id:
                await publish_result(test_session_id, str(webhook.id), "failed", {"status_code": 401, "detail": "Webhook secret is required"})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook secret is required",
            )

        if not webhook.secret_hash:
            if test_session_id:
                await publish_result(test_session_id, str(webhook.id), "failed", {"status_code": 500, "detail": "Webhook authentication is not configured correctly"})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook authentication is not configured correctly",
            )

        if not verify_webhook_secret(
            secret=x_relay_secret,
            secret_hash=webhook.secret_hash,
        ):
            if test_session_id:
                await publish_result(test_session_id, str(webhook.id), "failed", {"status_code": 401, "detail": "Invalid webhook secret"})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret",
            )

    # 4. Read the incoming test payload
    try:
        payload = await request.json()
    except Exception:
        if test_session_id:
            await publish_result(test_session_id, str(webhook.id), "failed", {"status_code": 400, "detail": "Request body must be valid JSON"})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body must be valid JSON")

    # 5. Return the received payload to the caller and mirror it to the active UI session.
    result = {
        "received": True,
        "webhook_id": str(webhook.id),
        "payload": payload,
    }
    if test_session_id:
        await publish_result(test_session_id, str(webhook.id), "success", result)
    return result
