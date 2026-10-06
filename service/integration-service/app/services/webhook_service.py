import secrets
import uuid

from pwdlib import PasswordHash

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.grpc.workflow_client import WorkflowGrpcClient
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookUpdate

password_hash = PasswordHash.recommended()


class WorkflowVersionNotFoundError(ValueError):
    pass


class UnpublishedWorkflowVersionError(ValueError):
    pass


class InactiveWorkflowError(ValueError):
    pass


async def validate_workflow_version(
    workflow_id: uuid.UUID,
    workflow_version_id: uuid.UUID,
    workspace_id: uuid.UUID,
    *,
    allow_draft: bool = False,
) -> tuple[str, str]:
    client = WorkflowGrpcClient()

    try:
        validation = await client.validate_workflow_version(
            workflow_id=str(workflow_id),
            version_id=str(workflow_version_id),
            workspace_id=str(workspace_id),
        )
    finally:
        await client.close()

    if not validation.valid:
        raise WorkflowVersionNotFoundError("Workflow or workflow version not found")
    version_status = validation.status.lower()
    workflow_status = validation.workflow_status.lower()
    if version_status != "published" and not (allow_draft and version_status == "draft"):
        raise UnpublishedWorkflowVersionError("Webhook workflow version must be published")
    if version_status == "published" and workflow_status != "active":
        raise InactiveWorkflowError("Workflow is inactive")
    return version_status, workflow_status


def generate_public_token() -> str:
    return secrets.token_urlsafe(32)

def generate_webhook_secret() -> str:
    return f"rly_whsec_{secrets.token_urlsafe(32)}"

def verify_webhook_secret(
    secret: str,
    secret_hash: str,
) -> bool:
    return password_hash.verify(secret, secret_hash)


async def create_webhook(
    data: WebhookCreate,
    workspace_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[Webhook, str | None]:
    version_status, _ = await validate_workflow_version(
        workflow_id=data.workflow_id,
        workflow_version_id=data.workflow_version_id,
        workspace_id=workspace_id,
        allow_draft=True,
    )

    secret = None
    secret_hash = None

    if data.authentication_type == "secret":
        secret = generate_webhook_secret()
        secret_hash = password_hash.hash(secret)

    webhook = Webhook(
        workspace_id=workspace_id,
        workflow_id=data.workflow_id,
        workflow_version_id=data.workflow_version_id,
        name=data.name,
        public_token=generate_public_token(),
        event_name=data.event_name,
        method=data.method,
        authentication_type=data.authentication_type,
        secret_hash=secret_hash,
        # Draft endpoints are provisioned immediately but cannot receive
        # traffic until their version is published.
        is_active=data.is_active and version_status == "published",
        activate_on_publish=version_status == "draft",
    )

    session.add(webhook)

    try:
        await session.commit()
        await session.refresh(webhook)
    except IntegrityError:
        await session.rollback()
        raise

    return webhook, secret


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


async def get_webhook_by_public_token(
    public_token: str,
    session: AsyncSession,
) -> Webhook | None:
    result = await session.execute(
        select(Webhook).where(
            Webhook.public_token == public_token,
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

    if (
        "workflow_id" in update_data
        or "workflow_version_id" in update_data
        or update_data.get("is_active") is True
    ):
        target_workflow_id = update_data.get("workflow_id", webhook.workflow_id)
        target_version_id = update_data.get("workflow_version_id", webhook.workflow_version_id)
        if target_workflow_id is None or target_version_id is None:
            raise WorkflowVersionNotFoundError("Workflow and workflow version are required")
        await validate_workflow_version(
            workflow_id=target_workflow_id,
            workflow_version_id=target_version_id,
            workspace_id=workspace_id,
        )

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


async def delete_workflow_webhooks(
    workflow_id: uuid.UUID,
    workspace_id: uuid.UUID,
    session: AsyncSession,
    workflow_version_id: uuid.UUID | None = None,
) -> int:
    """Revoke all webhook resources owned by a workflow or one version."""
    statement = delete(Webhook).where(
        Webhook.workflow_id == workflow_id,
        Webhook.workspace_id == workspace_id,
    )
    if workflow_version_id is not None:
        statement = statement.where(Webhook.workflow_version_id == workflow_version_id)

    try:
        result = await session.execute(statement)
        await session.commit()
        return result.rowcount or 0
    except Exception:
        await session.rollback()
        raise


async def activate_workflow_version_webhooks(
    workflow_id: uuid.UUID,
    workspace_id: uuid.UUID,
    workflow_version_id: uuid.UUID,
    session: AsyncSession,
) -> int:
    """Activate endpoints after their exact workflow version is published."""
    result = await session.execute(
        select(Webhook).where(
            Webhook.workflow_id == workflow_id,
            Webhook.workspace_id == workspace_id,
            Webhook.workflow_version_id == workflow_version_id,
            Webhook.activate_on_publish.is_(True),
        )
    )
    webhooks = list(result.scalars().all())
    for webhook in webhooks:
        webhook.is_active = True
        webhook.activate_on_publish = False
    try:
        await session.commit()
        return len(webhooks)
    except Exception:
        await session.rollback()
        raise


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
