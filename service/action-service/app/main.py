from fastapi import FastAPI

from app.routes.connections import router as connections_router


app = FastAPI(
    title="Relay Action Service",
)

app.include_router(connections_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "action-service",
    }
