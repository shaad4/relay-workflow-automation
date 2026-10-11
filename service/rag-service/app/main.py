from fastapi import FastAPI

from app.api.routes.knowledge_bases import (
    router as knowledge_base_router,
)

app = FastAPI(
    title="Relay RAG Service",
    version="1.0.0",
)

app.include_router(knowledge_base_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "rag-service",
    }