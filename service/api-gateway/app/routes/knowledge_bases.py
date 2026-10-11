
import os

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response


router = APIRouter(prefix="/knowledge-bases")

RAG_SERVICE_URL = os.getenv(
    "RAG_SERVICE_URL",
    "http://rag-service:8000",
)

HOP_BY_HOP_HEADERS = {
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
async def create_knowledge_base(request: Request):
    return await proxy_rag_request(request)


@router.get("/")
async def list_knowledge_bases(request: Request):
    return await proxy_rag_request(request)


async def proxy_rag_request(request: Request):
    url = f"{RAG_SERVICE_URL}/knowledge-bases/"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in {"host", "content-length"}
    }

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                method=request.method,
                url=url,
                content=await request.body(),
                headers=headers,
                params=request.query_params,
            )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="RAG Service unavailable",
        ) from exc

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in {
            "content-length",
            "content-encoding",
        }
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )
