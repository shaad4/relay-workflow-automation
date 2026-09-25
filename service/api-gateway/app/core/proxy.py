import os

import httpx
from fastapi import Request
from fastapi.responses import Response

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

# RFC 7230 hop-by-hop headers
HOP_BY_HOP_HEADERS: set[str] = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

# Headers that should not be forwarded from client to downstream
REQUEST_EXCLUDED_HEADERS: set[str] = HOP_BY_HOP_HEADERS | {
    "host",
    "content-length",
}

# Headers that should not be forwarded from downstream to client
RESPONSE_EXCLUDED_HEADERS: set[str] = HOP_BY_HOP_HEADERS | {
    "content-length",
    "content-encoding",
    "server",
    "date",
    "set-cookie",
    "access-control-allow-origin",
    "access-control-allow-credentials",
    "access-control-allow-methods",
    "access-control-allow-headers",
    "access-control-max-age",
    "access-control-expose-headers",
}


def build_proxy_response(response: httpx.Response) -> Response:
    forward_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in RESPONSE_EXCLUDED_HEADERS
    }

    proxy_res = Response(
        content=response.content,
        status_code=response.status_code,
        headers=forward_headers,
    )

    # Preserve all Set-Cookie headers individually
    for cookie in response.headers.get_list("set-cookie"):
        proxy_res.raw_headers.append((b"set-cookie", cookie.encode("latin-1")))

    return proxy_res


async def proxy_request(
    request: Request,
    target_url: str,
    follow_redirects: bool = True,
) -> Response:
    body = await request.body()

    forward_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in REQUEST_EXCLUDED_HEADERS
    }

    async with httpx.AsyncClient(
        follow_redirects=follow_redirects
    ) as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=forward_headers,
            params=request.query_params,
        )

    return build_proxy_response(response)
