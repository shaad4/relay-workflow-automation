
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.kafka.consumer import (
    start_consumer,
    stop_consumer,
    consume_workflow_triggered,
)

from app.routes.approvals import (
    router as approvals_router,
)
from app.routes.ai_provider_connections import (
    router as ai_provider_connections_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_consumer()

    consumer_task = asyncio.create_task(
        consume_workflow_triggered()
    )

    try:
        yield
    finally:
        consumer_task.cancel()

        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

        await stop_consumer()


app = FastAPI(
    title="Relay Execution Service",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def sanitize_ai_connection_validation(
    request: Request,
    exc: RequestValidationError,
):
    if request.url.path.startswith("/ai/connections"):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Invalid AI connection request",
            },
        )

    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": list(error["loc"]),
                    "msg": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
        },
    )


app.include_router(approvals_router)
app.include_router(ai_provider_connections_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "execution-service",
    }
