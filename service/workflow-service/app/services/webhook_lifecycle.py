from uuid import UUID

import grpc

from app.grpc.integration_client import IntegrationGrpcClient


class WebhookCleanupError(RuntimeError):
    """Integration Service could not confirm webhook endpoint revocation."""


async def revoke_workflow_webhooks(
    workflow_id: UUID,
    workspace_id: UUID | str,
    workflow_version_id: UUID | None = None,
) -> None:
    client = IntegrationGrpcClient()
    try:
        await client.delete_workflow_webhooks(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
            workflow_version_id=workflow_version_id,
        )
    except grpc.aio.AioRpcError as exc:
        raise WebhookCleanupError("Integration Service could not revoke webhook endpoints.") from exc
    finally:
        await client.close()
