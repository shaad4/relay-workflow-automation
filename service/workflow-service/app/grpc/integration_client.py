from uuid import UUID

import grpc

from app.config import grpc_target
from app.grpc.generated.integration import webhook_lifecycle_pb2, webhook_lifecycle_pb2_grpc

INTEGRATION_GRPC_URL = grpc_target("INTEGRATION_GRPC_URL", "integration-service:50053")


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

    async def activate_workflow_version_webhooks(
        self,
        workflow_id: UUID,
        workspace_id: UUID | str,
        workflow_version_id: UUID,
    ) -> int:
        request = webhook_lifecycle_pb2.DeleteWorkflowWebhooksRequest(
            workflow_id=str(workflow_id),
            workspace_id=str(workspace_id),
            workflow_version_id=str(workflow_version_id),
        )
        response = await self.stub.ActivateWorkflowVersionWebhooks(request, timeout=8.0)
        return response.activated_count

    async def sync_workflow_schedule(
        self,
        workflow_id: UUID,
        workspace_id: UUID | str,
        workflow_version_id: UUID,
        has_schedule_trigger: bool,
        workflow_active: bool,
    ) -> int:
        request = webhook_lifecycle_pb2.SyncWorkflowScheduleRequest(
            workflow_id=str(workflow_id),
            workspace_id=str(workspace_id),
            workflow_version_id=str(workflow_version_id),
            has_schedule_trigger=has_schedule_trigger,
            workflow_active=workflow_active,
        )

        response = await self.stub.SyncWorkflowSchedule(
            request,
            timeout=8.0,
        )

        return response.affected_count

    async def suspend_workflow_schedule(
        self,
        workflow_id: UUID,
        workspace_id: UUID | str,
    ) -> int:
        request = webhook_lifecycle_pb2.WorkflowScheduleLifecycleRequest(
            workflow_id=str(workflow_id),
            workspace_id=str(workspace_id),
        )

        response = await self.stub.SuspendWorkflowSchedule(
            request,
            timeout=8.0,
        )

        return response.affected_count

    async def delete_workflow_schedule(
        self,
        workflow_id: UUID,
        workspace_id: UUID | str,
    ) -> int:
        request = webhook_lifecycle_pb2.WorkflowScheduleLifecycleRequest(
            workflow_id=str(workflow_id),
            workspace_id=str(workspace_id),
        )

        response = await self.stub.DeleteWorkflowSchedule(
            request,
            timeout=8.0,
        )

        return response.affected_count

    async def close(self):
        await self.channel.close()
