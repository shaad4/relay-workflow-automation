from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from .webhooks import get_db
from app.services.webhook_service import (
    get_webhook_by_public_token,
    verify_webhook_secret,
)
from app.services.webhook_test_sessions import publish_result, publish_session_result

router = APIRouter(
    prefix="/hooks",
    tags=["public-webhooks"],
)


@router.post("/{public_token}")
async def receive_webhook(
    public_token: str,
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

    # 4. Webhook authentication succeeded
    return {
        "message": "Webhook authenticated successfully",
        "webhook_id": str(webhook.id),
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
