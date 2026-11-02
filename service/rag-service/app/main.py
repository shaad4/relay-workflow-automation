import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.documents import (
    router as document_router,
)
from app.api.routes.knowledge_bases import (
    router as knowledge_base_router,
)
from app.config import validate_startup
from app.grpc.rag_server import start_rag_grpc_server


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup()
    """Manage RAG gRPC server lifecycle."""

    # Start gRPC server
    grpc_server = await start_rag_grpc_server()

    try:
        yield

    finally:
        # Gracefully stop gRPC server
        await grpc_server.stop(grace=5)


app = FastAPI(
    title="Relay RAG Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Register API routers
app.include_router(knowledge_base_router)
app.include_router(document_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "rag-service",
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
