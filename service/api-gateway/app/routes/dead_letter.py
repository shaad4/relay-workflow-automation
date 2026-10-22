import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response


router = APIRouter(
    prefix="/dead-letter-events",
    tags=["Dead Letter Events"],
)

EXECUTION_SERVICE_URL = "http://execution-service:8000"

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
async def list_dead_letter_events(request: Request):
    url = f"{EXECUTION_SERVICE_URL}/dead-letter-events/"

    connection_headers = {
        name.strip().lower()
        for name in request.headers.get(
            "connection", ""
        ).split(",")
        if name.strip()
    }

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower()
        not in EXCLUDED_HEADERS | connection_headers
    }

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            response = await client.get(
                url,
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
        for name in response.headers.get(
            "connection", ""
        ).split(",")
        if name.strip()
    }

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower()
        not in EXCLUDED_HEADERS | response_connection_headers
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )
