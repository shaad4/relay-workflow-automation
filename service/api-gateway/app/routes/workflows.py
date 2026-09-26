from fastapi import APIRouter, Request
from fastapi.responses import Response
import httpx

router = APIRouter(prefix="/workflows")

WORKFLOW_SERVICE_URL = "http://workflow-service:8000"


@router.api_route("/", methods=["GET", "POST"])
async def workflows(request: Request):
    return await proxy_workflow_request(request, "")

@router.get("/{workflow_id}/")
async def get_workflow(request: Request, workflow_id: str):
    return await proxy_workflow_request(request, workflow_id)

@router.patch("/{workflow_id}/")
async def update_workflow(request: Request, workflow_id: str):
    return await proxy_workflow_request(request, workflow_id)

@router.delete("/{workflow_id}/")
async def delete_workflow(request: Request, workflow_id: str):
    return await proxy_workflow_request(request, workflow_id)

@router.get("/{workflow_id}/versions/")
async def list_workflow_versions(
    request: Request,
    workflow_id: str,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions",
    )

@router.get("/{workflow_id}/versions/{version_number}")
async def get_workflow_version(
    request: Request,
    workflow_id: str,
    version_number: int,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}",
    )

@router.post("/{workflow_id}/draft/")
async def create_workflow_draft(
    request: Request,
    workflow_id: str,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/draft",
    )

@router.post(
    "/{workflow_id}/versions/{version_number}/nodes/"
)
async def create_workflow_node(
    request: Request,
    workflow_id: str,
    version_number: int,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/nodes",
    )

@router.get(
    "/{workflow_id}/versions/{version_number}/nodes/"
)
async def list_workflow_nodes(
    request: Request,
    workflow_id: str,
    version_number: int,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/nodes",
    )

@router.patch(
    "/{workflow_id}/versions/{version_number}/nodes/{node_id}/"
)
async def update_workflow_node(
    request: Request,
    workflow_id: str,
    version_number: int,
    node_id: str,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/nodes/{node_id}",
    )


@router.delete(
    "/{workflow_id}/versions/{version_number}/nodes/{node_id}/"
)
async def delete_workflow_node(
    request: Request,
    workflow_id: str,
    version_number: int,
    node_id: str,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/nodes/{node_id}",
    )

@router.post(
    "/{workflow_id}/versions/{version_number}/edges/"
)
async def create_workflow_edge(
    request: Request,
    workflow_id: str,
    version_number: int,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/edges",
    )

@router.get(
    "/{workflow_id}/versions/{version_number}/edges/"
)
async def list_workflow_edges(
    request: Request,
    workflow_id: str,
    version_number: int,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/edges",
    )




async def proxy_workflow_request(
    request: Request,
    path: str,
):
    body = await request.body()

    url = f"{WORKFLOW_SERVICE_URL}/workflows"

    if path:
        url = f"{url}/{path}/"
    else:
        url = f"{url}/"

    print("PROXY METHOD:", request.method)
    print("PROXY URL:", url)

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