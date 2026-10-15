import json
from uuid import UUID

import grpc
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_identity
from app.grpc.workflow_client import WorkflowGrpcClient
from app.schemas.manual_trigger import ManualRunRequest


router = APIRouter(
    prefix="/workflows",
    tags=["manual-triggers"],
)


@router.post("/{workflow_id}/run")
async def run_workflow_manually(
    workflow_id: UUID,
    data: ManualRunRequest,
    identity: dict = Depends(get_current_identity),
):
    try:
        workspace_id = str(UUID(identity["workspace_id"]))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workspace identity",
        )

    client = WorkflowGrpcClient()

    try:
        published = await client.get_published_version(
            workflow_id=str(workflow_id),
            workspace_id=workspace_id,
        )

        definition = await client.get_workflow_definition(
            workflow_id=str(workflow_id),
            version_id=published.version_id,
            workspace_id=workspace_id,
        )

    except grpc.aio.AioRpcError as exc:
        if exc.code() == grpc.StatusCode.NOT_FOUND:
            raise HTTPException(
                status_code=404,
                detail="Workflow or published version not found",
            ) from exc

        if exc.code() == grpc.StatusCode.FAILED_PRECONDITION:
            raise HTTPException(
                status_code=409,
                detail="Workflow is not executable",
            ) from exc

        if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            raise HTTPException(
                status_code=504,
                detail="Workflow Service request timed out",
            ) from exc

        raise HTTPException(
            status_code=503,
            detail="Workflow Service unavailable",
        ) from exc

    finally:
        await client.close()

    try:
        nodes = json.loads(definition.nodes_json)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="Invalid workflow definition",
        )

    triggers = [
        node
        for node in nodes
        if node.get("node_type", "").startswith("trigger.")
    ]

    if (
        len(triggers) != 1
        or triggers[0]["node_type"] != "trigger.manual"
    ):
        raise HTTPException(
            status_code=409,
            detail="Published workflow does not have a Manual Trigger",
        )

    # Temporary response for STEP 175.
    # No execution or Kafka event is created yet.
    return {
        "status": "validated",
        "workflow_id": str(workflow_id),
        "workflow_version_id": published.version_id,
        "trigger_type": "manual",
        "input": data.input,
        "execution_started": False,
    }