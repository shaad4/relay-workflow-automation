from uuid import UUID

from fastapi import APIRouter, Request

from app.config import INTEGRATION_SERVICE_URL
from app.core.proxy import proxy_request

router = APIRouter(
    prefix="/workflows",
    tags=["manual-triggers"],
)


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
