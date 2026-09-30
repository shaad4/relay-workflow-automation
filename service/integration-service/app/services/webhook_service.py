import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.grpc.workflow_client import WorkflowGrpcClient
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookUpdate


async def validate_workflow_version(
    workflow_id: uuid.UUID,
    workflow_version_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    client = WorkflowGrpcClient()

    try:
        await client.validate_workflow_version(
            workflow_id=str(workflow_id),
            version_id=str(workflow_version_id),
            workspace_id=str(workspace_id),
        )
    finally:
        await client.close()


def generate_public_token() -> str:
    return secrets.token_urlsafe(32)


async def create_webhook(
    data: WebhookCreate,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> Webhook:
    await validate_workflow_version(
        workflow_id=data.workflow_id,
        workflow_version_id=data.workflow_version_id,
        workspace_id=workspace_id,
    )

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
        raise

    return webhook


async def list_webhooks(
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> list[Webhook]:
    result = await session.execute(
        select(Webhook)
        .where(Webhook.workspace_id == workspace_id)
        .order_by(Webhook.created_at.desc())
    )

    return list(result.scalars().all())

async def get_webhook(
    webhook_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> Webhook | None:
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.workspace_id == workspace_id,
        )
    )

    return result.scalar_one_or_none()


async def update_webhook(
    webhook_id: uuid.UUID,
    data: WebhookUpdate,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> Webhook | None:
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.workspace_id == workspace_id,
        )
    )

    webhook = result.scalar_one_or_none()

    if webhook is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(webhook, field, value)

    try:
        await session.commit()
        await session.refresh(webhook)
    except IntegrityError:
        await session.rollback()
        raise

    return webhook



async def delete_webhook(
    webhook_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> bool:
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.workspace_id == workspace_id,
        )
    )

    webhook = result.scalar_one_or_none()

    if webhook is None:
        return False

    await session.delete(webhook)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return True


async def regenerate_webhook_token(
    webhook_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> Webhook | None:
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.workspace_id == workspace_id,
        )
    )

    webhook = result.scalar_one_or_none()

    if webhook is None:
        return None

    webhook.public_token = generate_public_token()

    try:
        await session.commit()
        await session.refresh(webhook)
    except IntegrityError:
        await session.rollback()
        raise

    return webhook