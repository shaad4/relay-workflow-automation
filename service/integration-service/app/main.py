from fastapi import FastAPI

from app.routes.webhooks import router as webhook_router
from app.routes.public_webhooks import router as public_webhooks_router

app = FastAPI(
    title="Relay Integration Service",
)

app.include_router(webhook_router)
app.include_router(public_webhooks_router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "integration-service"}

