import grpc

from app.grpc.generated.workflow import workflow_pb2
from app.grpc.generated.workflow import workflow_pb2_grpc


WORKFLOW_SERVICE_ADDRESS = "workflow-service:50052"


class WorkflowClient:

    def __init__(self):
        self.channel = grpc.aio.insecure_channel(
            WORKFLOW_SERVICE_ADDRESS
        )

        self.stub = (
            workflow_pb2_grpc.WorkflowInternalServiceStub(
                self.channel
            )
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
            request
        )

    async def close(self):
        await self.channel.close()