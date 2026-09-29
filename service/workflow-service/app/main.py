from contextlib import asynccontextmanager

import os

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.dependencies import get_current_identity
from app.grpc.server import start_grpc_server
from app.routes.workflows import router as workflows_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = await start_grpc_server()

    try:
        yield
    finally:
        await grpc_server.stop(grace=5)


app = FastAPI(
    title="Relay Workflow Service",
    lifespan=lifespan,
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = {frontend_url.rstrip("/")}
if "localhost" in frontend_url:
    allowed_origins.add(frontend_url.replace("localhost", "127.0.0.1").rstrip("/"))
elif "127.0.0.1" in frontend_url:
    allowed_origins.add(frontend_url.replace("127.0.0.1", "localhost").rstrip("/"))


@app.middleware("http")
async def enforce_cookie_origin(request: Request, call_next):
    if (
        request.method not in {"GET", "HEAD", "OPTIONS", "TRACE"}
        and request.cookies.get("relay_access_token")
    ):
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site")
        origin_is_untrusted = origin and origin.rstrip("/") not in allowed_origins
        fetch_is_cross_site = not origin and fetch_site == "cross-site"
        if origin_is_untrusted or fetch_is_cross_site:
            return JSONResponse(
                status_code=403,
                content={"detail": "Untrusted request origin"},
            )
    return await call_next(request)

app.include_router(workflows_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "workflow-service"}


@app.get("/protected-test")
async def protected_test(
    identity: dict = Depends(get_current_identity),
):
    return {
        "message": "Authentication successful",
        "user_id": identity["user_id"],
        "workspace_id": identity["workspace_id"],
    }
