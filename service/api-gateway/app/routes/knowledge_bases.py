
import os
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response


router = APIRouter(prefix="/knowledge-bases")

RAG_SERVICE_URL = os.getenv(
    "RAG_SERVICE_URL",
    "http://rag-service:8000",
).rstrip("/")


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


# --------------------------------------------------
# Knowledge Base Routes
# --------------------------------------------------

@router.post("/")
async def create_knowledge_base(request: Request):
    return await proxy_rag_request(request)


@router.get("/")
async def list_knowledge_bases(request: Request):
    return await proxy_rag_request(request)


@router.get("/{knowledge_base_id}/")
async def get_knowledge_base(
    request: Request,
    knowledge_base_id: UUID,
):
    return await proxy_rag_request(
        request,
        path=str(knowledge_base_id),
    )

@router.delete("/{knowledge_base_id}/")
async def delete_knowledge_base(
    request: Request,
    knowledge_base_id: UUID,
):
    return await proxy_rag_request(
        request,
        path=str(knowledge_base_id),
    )


@router.post("/{knowledge_base_id}/documents/")
async def upload_document(
    request: Request,
    knowledge_base_id: UUID,
):
    return await proxy_rag_request(
        request,
        path=f"{knowledge_base_id}/documents",
    )

@router.post("/{knowledge_base_id}/search/")
async def search_knowledge_base(
    request: Request,
    knowledge_base_id: UUID,
):
    return await proxy_rag_request(
        request,
        path=f"{knowledge_base_id}/search",
    )

@router.get("/{knowledge_base_id}/documents/")
async def list_documents(
    request: Request,
    knowledge_base_id: UUID,
):
    return await proxy_rag_request(
        request,
        path=f"{knowledge_base_id}/documents",
    )

@router.delete(
    "/{knowledge_base_id}/documents/{document_id}/"
)
async def delete_document(
    request: Request,
    knowledge_base_id: UUID,
    document_id: UUID,
):
    return await proxy_rag_request(
        request,
        path=f"{knowledge_base_id}/documents/{document_id}",
    )

# --------------------------------------------------
# RAG Service Proxy
# --------------------------------------------------

async def proxy_rag_request(
    request: Request,
    path: str = "",
):
    # Validate and encode path segments
    path_segments = path.split("/") if path else []

    if any(segment in {".", ".."} for segment in path_segments):
        raise HTTPException(
            status_code=400,
            detail="Invalid RAG path",
        )

    from urllib.parse import quote

    encoded_path = "/".join(
        quote(segment, safe="")
        for segment in path_segments
    )

    base_url = f"{RAG_SERVICE_URL}/knowledge-bases"

    url = (
        f"{base_url}/{encoded_path}/"
        if encoded_path
        else f"{base_url}/"
    )

    # Forward request headers
    excluded_request_headers = HOP_BY_HOP_HEADERS | {
        "host",
        "content-length",
    }

    # Headers listed in Connection are also hop-by-hop
    connection_headers = {
        name.strip().lower()
        for name in request.headers.get("connection", "").split(",")
        if name.strip()
    }

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower()
        not in excluded_request_headers | connection_headers
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

    # Filter response headers
    excluded_response_headers = HOP_BY_HOP_HEADERS | {
        "content-length",
        "content-encoding",
    }

    response_connection_headers = {
        name.strip().lower()
        for name in response.headers.get("connection", "").split(",")
        if name.strip()
    }

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower()
        not in excluded_response_headers | response_connection_headers
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )
