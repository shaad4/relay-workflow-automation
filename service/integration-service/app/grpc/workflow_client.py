import grpc

from app.config import grpc_target
from app.grpc.generated.workflow import workflow_pb2, workflow_pb2_grpc

WORKFLOW_GRPC_URL = grpc_target("WORKFLOW_GRPC_URL", "workflow-service:50052")


class WorkflowGrpcClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(WORKFLOW_GRPC_URL)
        self.stub = workflow_pb2_grpc.WorkflowInternalServiceStub(self.channel)

    async def validate_workflow_version(
        self,
        workflow_id: str,
        version_id: str,
        workspace_id: str,
    ):
        request = workflow_pb2.ValidateWorkflowVersionRequest(
            workflow_id=workflow_id,
            version_id=version_id,
            workspace_id=workspace_id,
        )

        return await self.stub.ValidateWorkflowVersion(request)

    async def get_published_version(
        self,
        workflow_id: str,
        workspace_id: str,
    ):
        request = workflow_pb2.GetPublishedVersionRequest(
            workflow_id=workflow_id,
            workspace_id=workspace_id,
        )

        return await self.stub.GetPublishedVersion(
            request,
            timeout=10,
        )

    async def get_workflow_definition(
        self,
        workflow_id: str,
        version_id: str,
        workspace_id: str,
    ):
        request = workflow_pb2.GetWorkflowDefinitionRequest(
            workflow_id=workflow_id,
            version_id=version_id,
            workspace_id=workspace_id,
        )

        return await self.stub.GetWorkflowDefinition(
            request,
            timeout=10,
        )

    async def close(self):
        await self.channel.close()
