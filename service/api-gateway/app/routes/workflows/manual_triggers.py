from uuid import UUID

from fastapi import APIRouter, Request

from app.core.proxy import proxy_request

router = APIRouter(
    prefix="/workflows",
    tags=["manual-triggers"],
)

INTEGRATION_SERVICE_URL = "http://integration-service:8000"


@router.post("/{workflow_id}/run")
async def run_workflow_manually(
    request: Request,
    workflow_id: UUID,
):
    return await proxy_request(
        request,
        f"{INTEGRATION_SERVICE_URL}/workflows/{workflow_id}/run",
        follow_redirects=False,
    )
