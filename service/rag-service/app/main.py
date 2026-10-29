from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.documents import (
    router as document_router,
)
from app.api.routes.knowledge_bases import (
    router as knowledge_base_router,
)
from app.grpc.rag_server import start_rag_grpc_server


@asynccontextmanager
async def lifespan(app: FastAPI):
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
