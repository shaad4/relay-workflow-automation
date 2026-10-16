from uuid import UUID

from fastapi import APIRouter, Request

from app.core.proxy import proxy_request


router = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
)

INTEGRATION_SERVICE_URL = "http://integration-service:8000"


@router.post("/")
async def create_schedule(
    request: Request,
):
    return await proxy_request(
        request,
        f"{INTEGRATION_SERVICE_URL}/schedules/",
        follow_redirects=False,
    )


@router.get("/")
async def list_workflow_schedules(
    request: Request,
):
    return await proxy_request(
        request,
        f"{INTEGRATION_SERVICE_URL}/schedules/",
        follow_redirects=False,
    )


@router.get("/{schedule_id}")
async def get_workflow_schedule(
    request: Request,
    schedule_id: UUID,
):
    return await proxy_request(
        request,
        f"{INTEGRATION_SERVICE_URL}/schedules/{schedule_id}",
        follow_redirects=False,
    )

@router.patch("/{schedule_id}")
async def update_workflow_schedule(
    request: Request,
    schedule_id: UUID,
):
    return await proxy_request(
        request,
        f"{INTEGRATION_SERVICE_URL}/schedules/{schedule_id}",
        follow_redirects=False,
    )


@router.delete("/{schedule_id}")
async def delete_workflow_schedule(
    request: Request,
    schedule_id: UUID,
):
    return await proxy_request(
        request,
        f"{INTEGRATION_SERVICE_URL}/schedules/{schedule_id}",
        follow_redirects=False,
    )