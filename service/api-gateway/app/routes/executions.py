
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response


router = APIRouter(prefix="/executions")

EXECUTION_SERVICE_URL = "http://execution-service:8000"


@router.get("/")
async def list_executions(request: Request):
    return await proxy_execution_request(request, "")


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

    encoded_path = "/".join(
        quote(segment, safe="")
        for segment in path_segments
    )

    url = f"{EXECUTION_SERVICE_URL}/executions"
    url = f"{url}/{encoded_path}" if encoded_path else url

    excluded_headers = {
        "host",
        "content-length",
        "connection",
        "transfer-encoding",
        "content-encoding",
    }

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in excluded_headers
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

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Execution Service unavailable",
        ) from exc

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={
            key: value
            for key, value in response.headers.items()
            if key.lower() not in excluded_headers
        },
    )
