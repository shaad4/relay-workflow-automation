from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.grpc.server import start_grpc_server
from app.routes.connections import router as connections_router
from app.routes.gmail_oauth import router as gmail_oauth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = await start_grpc_server()

    yield

    await grpc_server.stop(grace=5)


app = FastAPI(
    title="Relay Action Service",
    lifespan=lifespan,
)

app.include_router(connections_router)
app.include_router(gmail_oauth_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "action-service",
    }