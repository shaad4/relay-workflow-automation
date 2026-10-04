import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.kafka.consumer import (
    start_consumer,
    stop_consumer,
    consume_workflow_triggered,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_consumer()

    consumer_task = asyncio.create_task(
        consume_workflow_triggered()
    )

    yield

    consumer_task.cancel()

    await stop_consumer()


app = FastAPI(
    title="Relay Execution Service",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "execution-service",
    }