import grpc

from app.grpc.generated.workflow import workflow_pb2
from app.grpc.generated.workflow import workflow_pb2_grpc


WORKFLOW_GRPC_URL = "workflow-service:50052"


class WorkflowGrpcClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(WORKFLOW_GRPC_URL)
        self.stub = workflow_pb2_grpc.WorkflowInternalServiceStub(
            self.channel
        )

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

    async def close(self):
        await self.channel.close()