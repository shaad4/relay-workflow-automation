import httpx

from fastapi import APIRouter, Request
from fastapi.responses import Response


router = APIRouter(
    prefix="/connections",
    tags=["connections"],
)

ACTION_SERVICE_URL = "http://action-service:8000"

HOP_BY_HOP_HEADERS = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}



@router.post("/")
async def create_connection(request: Request):
    return await proxy_action_request(request, "")

@router.get("/")
async def get_connections(request: Request):
    return await proxy_action_request(request, "")

@router.get("/{connection_id}/")
async def get_connection(connection_id: str, request: Request):
    return await proxy_action_request(request, connection_id)

@router.patch("/{connection_id}/")
async def update_connection(connection_id: str, request: Request):
    return await proxy_action_request(request, connection_id)

@router.delete("/{connection_id}/")
async def delete_connection(connection_id: str, request: Request):
    return await proxy_action_request(request, connection_id)

@router.post("/{connection_id}/test/")
async def test_connection(connection_id: str, request: Request):
    return await proxy_action_request(
        request,
        f"{connection_id}/test",
    )

@router.get("/gmail/oauth/start")
async def start_gmail_oauth(request: Request):
    url = f"{ACTION_SERVICE_URL}/connections/gmail/oauth/start"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    async with httpx.AsyncClient(
        follow_redirects=False,
    ) as client:
        response = await client.get(
            url=url,
            headers=headers,
            params=request.query_params,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={
            key: value
            for key, value in response.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        },
        media_type=response.headers.get("content-type"),
    )

@router.get("/gmail/oauth/callback")
async def gmail_oauth_callback(request: Request):
    url = f"{ACTION_SERVICE_URL}/connections/gmail/oauth/callback"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    async with httpx.AsyncClient(
        follow_redirects=False,
    ) as client:
        response = await client.get(
            url=url,
            headers=headers,
            params=request.query_params,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={
            key: value
            for key, value in response.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        },
        media_type=response.headers.get("content-type"),
    )



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
        headers={
            key: value
            for key, value in response.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        },
        media_type=response.headers.get("content-type"),
    )