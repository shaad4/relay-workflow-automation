import grpc
import json
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.models.workflow_edge import WorkflowEdge
from app.models.workflow_node import WorkflowNode
from app.grpc.generated.workflow import workflow_pb2
from app.grpc.generated.workflow import workflow_pb2_grpc


class WorkflowInternalService(
    workflow_pb2_grpc.WorkflowInternalServiceServicer
):

    async def GetPublishedVersion(self, request, context):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Workflow).where(
                    Workflow.id == request.workflow_id,
                    Workflow.workspace_id == request.workspace_id,
                )
            )

            workflow = result.scalar_one_or_none()

            if not workflow or not workflow.published_version_id:
                context.set_code(
                    grpc.StatusCode.NOT_FOUND
                )
                context.set_details(
                    "Published workflow version not found"
                )
                return workflow_pb2.GetPublishedVersionResponse()

            version_result = await session.execute(
                select(WorkflowVersion).where(
                    WorkflowVersion.id == workflow.published_version_id,
                    WorkflowVersion.workflow_id == workflow.id,
                )
            )

            version = version_result.scalar_one_or_none()

            if not version:
                context.set_code(
                    grpc.StatusCode.NOT_FOUND
                )
                context.set_details(
                    "Published workflow version not found"
                )
                return workflow_pb2.GetPublishedVersionResponse()

            return workflow_pb2.GetPublishedVersionResponse(
                version_id=str(version.id),
                workflow_id=str(version.workflow_id),
                version=version.version,
                status=version.status,
            )

    async def GetWorkflowDefinition(self, request, context):
        async with AsyncSessionLocal() as session:
            workflow_result = await session.execute(
                select(Workflow).where(
                    Workflow.id == request.workflow_id,
                    Workflow.workspace_id == request.workspace_id,
                )
            )

            workflow = workflow_result.scalar_one_or_none()

            if not workflow:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Workflow not found")
                return workflow_pb2.GetWorkflowDefinitionResponse()

            version_result = await session.execute(
                select(WorkflowVersion).where(
                    WorkflowVersion.id == request.version_id,
                    WorkflowVersion.workflow_id == workflow.id,
                )
            )

            version = version_result.scalar_one_or_none()

            if not version:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Workflow version not found")
                return workflow_pb2.GetWorkflowDefinitionResponse()

            if version.status.lower() != "published":
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("Workflow version is not published")
                return workflow_pb2.GetWorkflowDefinitionResponse()

            if workflow.status.lower() != "active":
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("Workflow is inactive")
                return workflow_pb2.GetWorkflowDefinitionResponse()

            nodes_result = await session.execute(
                select(WorkflowNode).where(
                    WorkflowNode.workflow_version_id == version.id,
                )
            )

            nodes = nodes_result.scalars().all()

            edges_result = await session.execute(
                select(WorkflowEdge).where(
                    WorkflowEdge.workflow_version_id == version.id,
                )
            )

            edges = edges_result.scalars().all()

            nodes_data = [
                {
                    "id": str(node.id),
                    "workflow_version_id": str(node.workflow_version_id),
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "label": node.label,
                    "position_x": node.position_x,
                    "position_y": node.position_y,
                    "configuration": node.configuration,
                }
                for node in nodes
            ]

            edges_data = [
                {
                    "id": str(edge.id),
                    "workflow_version_id": str(edge.workflow_version_id),
                    "source_node_id": edge.source_node_id,
                    "target_node_id": edge.target_node_id,
                    "condition": edge.condition,
                }
                for edge in edges
            ]

            return workflow_pb2.GetWorkflowDefinitionResponse(
                version_id=str(version.id),
                workflow_id=str(version.workflow_id),
                version=version.version,
                status=version.status,
                nodes_json=json.dumps(nodes_data),
                edges_json=json.dumps(edges_data),
            )


    async def ValidateWorkflowVersion(self, request, context):
        async with AsyncSessionLocal() as session:
            workflow_result = await session.execute(
                select(Workflow).where(
                    Workflow.id == request.workflow_id,
                    Workflow.workspace_id == request.workspace_id,
                )
            )

            workflow = workflow_result.scalar_one_or_none()

            if not workflow:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Workflow not found")
                return workflow_pb2.ValidateWorkflowVersionResponse(
                    valid=False,
                )

            version_result = await session.execute(
                select(WorkflowVersion).where(
                    WorkflowVersion.id == request.version_id,
                    WorkflowVersion.workflow_id == workflow.id,
                )
            )

            version = version_result.scalar_one_or_none()

            if not version:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Workflow version not found")
                return workflow_pb2.ValidateWorkflowVersionResponse(
                    valid=False,
                )

            return workflow_pb2.ValidateWorkflowVersionResponse(
                valid=True,
                workflow_id=str(workflow.id),
                version_id=str(version.id),
                version=version.version,
                status=version.status,
                workflow_status=workflow.status,
            )
