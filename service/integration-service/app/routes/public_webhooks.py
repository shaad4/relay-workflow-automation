from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .webhooks import get_db
from app.services.webhook_service import (
    get_webhook_by_public_token,
    verify_webhook_secret,
)

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