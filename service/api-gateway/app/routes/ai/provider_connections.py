import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.config import EXECUTION_SERVICE_URL

router = APIRouter(
    prefix="/ai/connections",
    tags=["AI Provider Connections"],
)


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


async def proxy_ai_connection_request(
    request: Request,
    path: str = "",
):
    segments = path.split("/") if path else []

    if any(segment in {".", ".."} for segment in segments):
        raise HTTPException(
            status_code=400,
            detail="Invalid AI connection path",
        )

    url = f"{EXECUTION_SERVICE_URL}/ai/connections/"

    if path:
        url = f"{url}{path}/"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    body = await request.body()

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                params=request.query_params,
            )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI connection service unavailable",
        ) from exc

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={
            key: value
            for key, value in response.headers.items()
            if key.lower() not in HOP_BY_HOP_HEADERS
        },
    )


@router.post("/")
async def create_ai_connection(request: Request):
    return await proxy_ai_connection_request(request)


@router.get("/")
async def list_ai_connections(request: Request):
    return await proxy_ai_connection_request(request)


@router.get("/{connection_id}/")
async def get_ai_connection(
    connection_id: str,
    request: Request,
):
    return await proxy_ai_connection_request(
        request,
        connection_id,
    )


@router.patch("/{connection_id}/")
async def update_ai_connection(
    connection_id: str,
    request: Request,
):
    return await proxy_ai_connection_request(
        request,
        connection_id,
    )


@router.delete("/{connection_id}/")
async def delete_ai_connection(
    connection_id: str,
    request: Request,
):
    return await proxy_ai_connection_request(
        request,
        connection_id,
    )


@router.post("/{connection_id}/test/")
async def test_ai_connection(
    connection_id: str,
    request: Request,
):
    return await proxy_ai_connection_request(
        request,
        f"{connection_id}/test",
    )


@router.get("/{connection_id}/models/")
async def get_ai_connection_models(
    connection_id: str,
    request: Request,
):
    return await proxy_ai_connection_request(
        request,
        f"{connection_id}/models",
    )
