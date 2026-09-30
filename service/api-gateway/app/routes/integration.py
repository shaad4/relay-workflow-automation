import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

router = APIRouter(prefix="/webhooks")

INTEGRATION_SERVICE_URL = "http://integration-service:8000"


@router.post("/")
async def create_webhook(request: Request):
    return await proxy_integration_request(request, "")

@router.get("/")
async def list_webhooks(request: Request):
    return await proxy_integration_request(request, "")

@router.get("/{webhook_id}/")
async def get_webhook(request: Request, webhook_id: str):
    return await proxy_integration_request(
        request,
        webhook_id,
    )

@router.patch("/{webhook_id}/")
async def update_webhook(request: Request, webhook_id: str):
    return await proxy_integration_request(request, webhook_id)

@router.delete("/{webhook_id}/")
async def delete_webhook(request: Request, webhook_id: str):
    return await proxy_integration_request(request, webhook_id)


async def proxy_integration_request(
    request: Request,
    path: str,
):
    body = await request.body()

    path_segments = path.split("/") if path else []

    if any(segment in {".", ".."} for segment in path_segments):
        raise HTTPException(
            status_code=400,
            detail="Invalid integration path",
        )

    url = f"{INTEGRATION_SERVICE_URL}/webhooks"

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