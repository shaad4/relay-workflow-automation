from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

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


@router.patch(
    "/{workflow_id}/versions/{version_number}/edges/{edge_id}/"
)
async def update_workflow_edge(
    request: Request,
    workflow_id: str,
    version_number: int,
    edge_id: str,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/edges/{edge_id}",
    )

@router.delete(
    "/{workflow_id}/versions/{version_number}/edges/{edge_id}/"
)
async def delete_workflow_edge(
    request: Request,
    workflow_id: str,
    version_number: int,
    edge_id: str,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/edges/{edge_id}",
    )

@router.post(
    "/{workflow_id}/versions/{version_number}/validate/"
)
async def validate_workflow(
    request: Request,
    workflow_id: str,
    version_number: int,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/validate",
    )

@router.post("/{workflow_id}/versions/{version_number}/publish/")
async def publish_workflow_version(
    request: Request,
    workflow_id: str,
    version_number: int,
):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/versions/{version_number}/publish",
    )

@router.post("/{workflow_id}/deactivate/")
async def deactivate_workflow(request: Request, workflow_id: str):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/deactivate",
    )

@router.post("/{workflow_id}/activate/")
async def activate_workflow(request: Request, workflow_id: str):
    return await proxy_workflow_request(
        request,
        f"{workflow_id}/activate",
    )


async def proxy_workflow_request(
    request: Request,
    path: str,
):
    body = await request.body()

    path_segments = path.split("/") if path else []
    if any(segment in {".", ".."} for segment in path_segments):
        raise HTTPException(status_code=400, detail="Invalid workflow path")

    encoded_path = "/".join(quote(segment, safe="") for segment in path_segments)
    url = f"{WORKFLOW_SERVICE_URL}/workflows"
    url = f"{url}/{encoded_path}/" if encoded_path else f"{url}/"

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
