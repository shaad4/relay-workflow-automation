from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.config import EXECUTION_SERVICE_URL

router = APIRouter(prefix="/executions")


EXCLUDED_HEADERS = {
    "host",
    "content-length",
    "content-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


@router.get("/")
async def list_executions(request: Request):
    return await proxy_execution_request(request, "")


@router.get("/{execution_id}/")
async def get_execution_details(
    request: Request,
    execution_id: str,
):
    return await proxy_execution_request(
        request,
        execution_id,
    )


@router.get("/{execution_id}/steps/")
async def get_execution_steps(
    request: Request,
    execution_id: str,
):
    return await proxy_execution_request(
        request,
        f"{execution_id}/steps",
    )


@router.post("/{execution_id}/cancel/")
async def cancel_execution(request: Request, execution_id: str):
    return await proxy_execution_request(request, f"{execution_id}/cancel")


async def proxy_execution_request(
    request: Request,
    path: str,
):
    path_segments = path.split("/") if path else []

    if any(segment in {".", ".."} for segment in path_segments):
        raise HTTPException(
            status_code=400,
            detail="Invalid execution path",
        )

    encoded_path = "/".join(quote(segment, safe="") for segment in path_segments)

    base_url = f"{EXECUTION_SERVICE_URL}/executions"

    url = f"{base_url}/{encoded_path}/" if encoded_path else f"{base_url}/"

    connection_headers = {
        name.strip().lower()
        for name in request.headers.get("connection", "").split(",")
        if name.strip()
    }

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in EXCLUDED_HEADERS | connection_headers
    }

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
            )

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Execution Service request timed out",
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Execution Service unavailable",
        ) from exc

    response_connection_headers = {
        name.strip().lower()
        for name in response.headers.get("connection", "").split(",")
        if name.strip()
    }

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in EXCLUDED_HEADERS | response_connection_headers
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )
