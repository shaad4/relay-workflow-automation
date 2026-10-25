
import re

import httpx

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response


router = APIRouter(
    prefix="/hooks",
    tags=["public-webhooks"],
)

INTEGRATION_SERVICE_URL = "http://integration-service:8000"

WEBHOOK_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


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


def validate_webhook_token(public_token: str) -> None:
    if not WEBHOOK_TOKEN_PATTERN.fullmatch(public_token):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook token",
        )


async def proxy_public_webhook_request(
    request: Request,
    path: str,
) -> Response:
    body = await request.body()

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    url = f"{INTEGRATION_SERVICE_URL}/hooks/{path}"

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )


@router.api_route("/{public_token}", methods=["POST"])
async def receive_public_webhook(
    public_token: str,
    request: Request,
):
    validate_webhook_token(public_token)

    return await proxy_public_webhook_request(
        request=request,
        path=public_token,
    )


@router.api_route("/{public_token}/test", methods=["POST"])
async def test_public_webhook(
    public_token: str,
    request: Request,
):
    validate_webhook_token(public_token)

    return await proxy_public_webhook_request(
        request=request,
        path=f"{public_token}/test",
    )
