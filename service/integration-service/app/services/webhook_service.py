import secrets
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookUpdate


def generate_public_token() -> str:
    return secrets.token_urlsafe(32)

async def create_webhook(
    data: WebhookCreate,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> Webhook:
    webhook = Webhook(
        workspace_id=workspace_id,
        workflow_id=data.workflow_id,
        workflow_version_id=data.workflow_version_id,
        name=data.name,
        public_token=generate_public_token(),
        event_name=data.event_name,
        method=data.method,
        authentication_type=data.authentication_type,
        secret_ref=data.secret_ref,
        is_active=data.is_active,
    )

    session.add(webhook)

    try:
        await session.commit()
        await session.refresh(webhook)
    except IntegrityError:
        await session.rollback()
        raise ValueError("Failed to create webhook")

    return webhook
