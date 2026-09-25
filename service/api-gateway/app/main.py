from fastapi import FastAPI, Request
from fastapi.responses import Response
import httpx

app = FastAPI(
    title="Relay API Gateway",
    version="1.0.0",
)

AUTH_SERVICE_URL = "http://auth-service:8000"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "api-gateway",
    }


@app.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def auth_proxy(request: Request, path: str):
    url = f"{AUTH_SERVICE_URL}/auth/{path}"

    body = await request.body()

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