import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter(prefix="/approvals")

EXECUTION_SERVICE_URL = "http://execution-service:8000"


@router.get("/")
async def list_approvals(request: Request):
    return await proxy_execution_request(request, "")

@router.get("/{approval_id}/")
async def get_approval(request: Request, approval_id: str):
    return await proxy_execution_request(
        request,
        approval_id,
    )


async def proxy_execution_request(
    request: Request,
    path: str,
):
    body = await request.body()

    path_segments = path.split("/") if path else []

    if any(segment in {".", ".."} for segment in path_segments):
        raise HTTPException(
            status_code=400,
            detail="Invalid execution path",
        )

    url = f"{EXECUTION_SERVICE_URL}/approvals"

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