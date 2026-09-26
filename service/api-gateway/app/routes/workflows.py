from fastapi import APIRouter, Request
from fastapi.responses import Response
import httpx

router = APIRouter(prefix="/workflows")

WORKFLOW_SERVICE_URL = "http://workflow-service:8000"


@router.api_route("/", methods=["GET", "POST"])
async def workflows(request: Request):
    return await proxy_workflow_request(request, "")


async def proxy_workflow_request(
    request: Request,
    path: str,
):
    body = await request.body()

    url = f"{WORKFLOW_SERVICE_URL}/workflows/"

    if path:
        url = f"{url}/{path}"

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