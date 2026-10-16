from uuid import UUID

import grpc

from app.grpc.generated.integration import webhook_lifecycle_pb2
from app.grpc.generated.integration import webhook_lifecycle_pb2_grpc
from app.db.database import AsyncSessionLocal
from app.services.webhook_service import activate_workflow_version_webhooks, delete_workflow_webhooks
from app.services.workflow_schedule_service import (
    sync_workflow_schedule,
    suspend_workflow_schedule,
    delete_workflow_schedule,
)


class IntegrationInternalService(
    webhook_lifecycle_pb2_grpc.IntegrationInternalServiceServicer
):
    async def DeleteWorkflowWebhooks(self, request, context):
        try:
            workflow_id = UUID(request.workflow_id)
            workspace_id = UUID(request.workspace_id)
            workflow_version_id = UUID(request.workflow_version_id) if request.workflow_version_id else None
        except (ValueError, TypeError):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid workflow cleanup identifiers")
            return webhook_lifecycle_pb2.DeleteWorkflowWebhooksResponse()

        try:
            async with AsyncSessionLocal() as session:
                deleted_count = await delete_workflow_webhooks(
                    workflow_id=workflow_id,
                    workspace_id=workspace_id,
                    workflow_version_id=workflow_version_id,
                    session=session,
                )

            return webhook_lifecycle_pb2.DeleteWorkflowWebhooksResponse(
                deleted_count=deleted_count
            )
        except Exception:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Webhook cleanup failed")
            return webhook_lifecycle_pb2.DeleteWorkflowWebhooksResponse()

    async def ActivateWorkflowVersionWebhooks(self, request, context):
        try:
            workflow_id = UUID(request.workflow_id)
            workspace_id = UUID(request.workspace_id)
            workflow_version_id = UUID(request.workflow_version_id)
        except (ValueError, TypeError):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Invalid workflow activation identifiers")
            return webhook_lifecycle_pb2.ActivateWorkflowVersionWebhooksResponse()

        try:
            async with AsyncSessionLocal() as session:
                activated_count = await activate_workflow_version_webhooks(
                    workflow_id=workflow_id,
                    workspace_id=workspace_id,
                    workflow_version_id=workflow_version_id,
                    session=session,
                )
            return webhook_lifecycle_pb2.ActivateWorkflowVersionWebhooksResponse(
                activated_count=activated_count
            )
        except Exception:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Webhook activation failed")
            return webhook_lifecycle_pb2.ActivateWorkflowVersionWebhooksResponse()


    async def SyncWorkflowSchedule(self, request, context):
        try:
            workflow_id = UUID(request.workflow_id)
            workspace_id = UUID(request.workspace_id)
            workflow_version_id = UUID(
                request.workflow_version_id
            )
        except (ValueError, TypeError):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid workflow identifiers",
            )

        try:
            async with AsyncSessionLocal() as session:
                count = await sync_workflow_schedule(
                    workflow_id=workflow_id,
                    workspace_id=workspace_id,
                    workflow_version_id=workflow_version_id,
                    has_schedule_trigger=request.has_schedule_trigger,
                    workflow_active=request.workflow_active,
                    session=session,
                )

            return webhook_lifecycle_pb2.WorkflowScheduleLifecycleResponse(
                affected_count=count
            )

        except Exception:
            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Schedule synchronization failed",
            )

    async def SuspendWorkflowSchedule(self, request, context):
        try:
            workflow_id = UUID(request.workflow_id)
            workspace_id = UUID(request.workspace_id)
        except (ValueError, TypeError):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid workflow identifiers",
            )

        try:
            async with AsyncSessionLocal() as session:
                count = await suspend_workflow_schedule(
                    workflow_id=workflow_id,
                    workspace_id=workspace_id,
                    session=session,
                )

            return webhook_lifecycle_pb2.WorkflowScheduleLifecycleResponse(
                affected_count=count
            )

        except Exception:
            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Schedule suspension failed",
            )

    async def DeleteWorkflowSchedule(self, request, context):
        try:
            workflow_id = UUID(request.workflow_id)
            workspace_id = UUID(request.workspace_id)
        except (ValueError, TypeError):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid workflow identifiers",
            )

        try:
            async with AsyncSessionLocal() as session:
                count = await delete_workflow_schedule(
                    workflow_id=workflow_id,
                    workspace_id=workspace_id,
                    session=session,
                )

            return webhook_lifecycle_pb2.WorkflowScheduleLifecycleResponse(
                affected_count=count
            )

        except Exception:
            await context.abort(
                grpc.StatusCode.INTERNAL,
                "Schedule deletion failed",
            )
