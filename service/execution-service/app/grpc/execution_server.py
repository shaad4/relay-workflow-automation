from uuid import UUID

import grpc
from sqlalchemy import delete, select

from app.db.database import AsyncSessionLocal
from app.models.execution import Execution
from app.models.human_approval import HumanApproval
from app.grpc.generated.execution import approval_lifecycle_pb2
from app.grpc.generated.execution import approval_lifecycle_pb2_grpc


class ExecutionInternalService(
    approval_lifecycle_pb2_grpc.ExecutionInternalServiceServicer
):
    async def DeleteWorkflowApprovals(self, request, context):
        try:
            workflow_id = UUID(request.workflow_id)
            workspace_id = UUID(request.workspace_id)
        except ValueError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid workflow or workspace ID")

        async with AsyncSessionLocal() as session:
            execution_ids = select(Execution.id).where(
                Execution.workflow_id == workflow_id,
                Execution.workspace_id == workspace_id,
            )
            try:
                result = await session.execute(
                    delete(HumanApproval).where(
                        HumanApproval.workspace_id == workspace_id,
                        HumanApproval.execution_id.in_(execution_ids),
                    )
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise

        return approval_lifecycle_pb2.DeleteWorkflowApprovalsResponse(
            deleted_count=result.rowcount,
        )
