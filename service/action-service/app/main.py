import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import validate_startup
from app.grpc.server import start_grpc_server
from app.routes.connections import router as connections_router
from app.routes.gmail_oauth import router as gmail_oauth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup()
    grpc_server = await start_grpc_server()

    try:
        yield
    finally:
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
