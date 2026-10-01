from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.kafka.producer import start_producer, stop_producer
from app.grpc.server import start_grpc_server
from app.routes.webhooks import router as webhook_router
from app.routes.public_webhooks import router as public_webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()
    grpc_server = None
    try:
        grpc_server = await start_grpc_server()
        yield
    finally:
        if grpc_server is not None:
            await grpc_server.stop(grace=5)
        await stop_producer()


app = FastAPI(
    title="Relay Integration Service",
    lifespan=lifespan,
)

app.include_router(webhook_router)
app.include_router(public_webhooks_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "integration-service"}
