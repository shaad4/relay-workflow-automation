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