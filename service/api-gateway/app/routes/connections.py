import httpx

from fastapi import APIRouter, Request
from fastapi.responses import Response


router = APIRouter(
    prefix="/connections",
    tags=["connections"],
)

ACTION_SERVICE_URL = "http://action-service:8000"


@router.post("/")
async def create_connection(request: Request):
    return await proxy_action_request(request, "")

@router.get("/")
async def get_connections(request: Request):
    return await proxy_action_request(request, "")

@router.get("/{connection_id}/")
async def get_connection(connection_id: str, request: Request):
    return await proxy_action_request(request, connection_id)

async def proxy_action_request(
    request: Request,
    path: str,
):
    body = await request.body()

    url = f"{ACTION_SERVICE_URL}/connections"

    if path:
        url = f"{url}/{path}/"
    else:
        url = f"{url}/"

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            content=body,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() != "host"
            },
            params=request.query_params,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )