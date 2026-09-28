from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

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