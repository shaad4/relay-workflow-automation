import os
from uuid import UUID

import grpc

from app.grpc.generated.integration import webhook_lifecycle_pb2
from app.grpc.generated.integration import webhook_lifecycle_pb2_grpc


INTEGRATION_GRPC_URL = os.getenv("INTEGRATION_GRPC_URL", "integration-service:50053")


class IntegrationGrpcClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(INTEGRATION_GRPC_URL)
        self.stub = webhook_lifecycle_pb2_grpc.IntegrationInternalServiceStub(self.channel)

    async def delete_workflow_webhooks(
        self,
        workflow_id: UUID,
        workspace_id: UUID | str,
        workflow_version_id: UUID | None = None,
    ) -> int:
        request = webhook_lifecycle_pb2.DeleteWorkflowWebhooksRequest(
            workflow_id=str(workflow_id),
            workspace_id=str(workspace_id),
            workflow_version_id=str(workflow_version_id) if workflow_version_id else "",
        )
        response = await self.stub.DeleteWorkflowWebhooks(request, timeout=8.0)
        return response.deleted_count

    async def close(self):
        await self.channel.close()
