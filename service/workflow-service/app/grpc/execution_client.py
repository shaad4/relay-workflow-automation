from uuid import UUID

import grpc

from app.config import grpc_target
from app.grpc.generated.execution import approval_lifecycle_pb2, approval_lifecycle_pb2_grpc

EXECUTION_GRPC_URL = grpc_target("EXECUTION_GRPC_URL", "execution-service:50055")


class ExecutionGrpcClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(EXECUTION_GRPC_URL)
        self.stub = approval_lifecycle_pb2_grpc.ExecutionInternalServiceStub(self.channel)

    async def delete_workflow_approvals(
        self,
        workflow_id: UUID,
        workspace_id: UUID | str,
    ) -> int:
        response = await self.stub.DeleteWorkflowApprovals(
            approval_lifecycle_pb2.DeleteWorkflowApprovalsRequest(
                workflow_id=str(workflow_id),
                workspace_id=str(workspace_id),
            ),
            timeout=8.0,
        )
        return response.deleted_count

    async def close(self):
        await self.channel.close()
