
import json
from uuid import UUID

import grpc
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import ValidationError

from app.dependencies import get_current_identity
from app.grpc.workflow_client import WorkflowGrpcClient
from app.schemas.manual_trigger import ManualRunRequest


router = APIRouter(
    prefix="/workflows",
    tags=["manual-triggers"],
)

MAX_MANUAL_PAYLOAD_BYTES = 64 * 1024


@router.post("/{workflow_id}/run")
async def run_workflow_manually(
    workflow_id: UUID,
    request: Request,
    identity: dict = Depends(get_current_identity),
):
    # 1. Validate Content-Type
    content_type = (
        request.headers.get("content-type", "")
        .split(";", 1)[0]
        .strip()
        .lower()
    )

    if content_type != "application/json":
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/json",
        )

    # 2. Check declared request size
    content_length = request.headers.get("content-length")

    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid Content-Length",
            )

        if declared_size < 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid Content-Length",
            )

        if declared_size > MAX_MANUAL_PAYLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Manual trigger payload exceeds 64 KiB",
            )

    # 3. Read body with actual size enforcement
    body = bytearray()

    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_MANUAL_PAYLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Manual trigger payload exceeds 64 KiB",
            )

        body.extend(chunk)

    # 4. Parse JSON
    try:
        raw_data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=422,
            detail="Invalid JSON request body",
        )

    # 5. Validate request schema
    try:
        data = ManualRunRequest.model_validate(raw_data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(
                include_input=False,
                include_context=False,
            ),
        ) from exc

    # 6. Resolve authenticated workspace
    try:
        workspace_id = str(UUID(identity["workspace_id"]))
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workspace identity",
        )

    # 7. Validate published workflow
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

    # 8. Parse workflow definition
    try:
        nodes = json.loads(definition.nodes_json)

        if not isinstance(nodes, list):
            raise ValueError("Nodes must be a list")

        if not all(isinstance(node, dict) for node in nodes):
            raise ValueError("Invalid node structure")

    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Invalid workflow definition",
        )

    # 9. Verify Manual Trigger
    triggers = [
        node
        for node in nodes
        if isinstance(node.get("node_type"), str)
        and node["node_type"].startswith("trigger.")
    ]

    if (
        len(triggers) != 1
        or triggers[0]["node_type"] != "trigger.manual"
    ):
        raise HTTPException(
            status_code=409,
            detail="Published workflow does not have a Manual Trigger",
        )

    # 10. Temporary validation-only response
    return {
        "status": "validated",
        "workflow_id": str(workflow_id),
        "workflow_version_id": published.version_id,
        "trigger_type": "manual",
        "input": data.input,
        "execution_started": False,
    }
