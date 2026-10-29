import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import validate_startup
from app.grpc.server import start_grpc_server
from app.kafka.producer import start_producer, stop_producer
from app.routes.manual_triggers import router as manual_triggers_router
from app.routes.public_webhooks import router as public_webhooks_router
from app.routes.schedules import router as schedules_router
from app.routes.webhooks import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup()
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
app.include_router(manual_triggers_router)
app.include_router(schedules_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "integration-service"}


@app.get("/health/live", include_in_schema=False)
async def liveness():
    """Process-only probe; dependency outages must not cause restart storms."""
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def readiness():
    """Bounded DB probe; no schema mutation or dependency details in responses."""
    from sqlalchemy import text

    from app.db.database import engine

    try:
        async with asyncio.timeout(3):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
