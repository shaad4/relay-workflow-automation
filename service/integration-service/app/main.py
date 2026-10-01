from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.kafka.producer import start_producer, stop_producer
from app.routes.webhooks import router as webhook_router
from app.routes.public_webhooks import router as public_webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer()

    yield

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


