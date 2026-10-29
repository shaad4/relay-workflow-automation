import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.grpc.server import start_grpc_server
from app.kafka.consumer import (
    consume_workflow_triggered,
    start_consumer,
    stop_consumer,
)
from app.kafka.lifecycle_producer import (
    start_lifecycle_producer,
    stop_lifecycle_producer,
)
from app.routes.ai_provider_connections import (
    router as ai_provider_connections_router,
)
from app.routes.approvals import (
    router as approvals_router,
)
from app.routes.dashboard import router as dashboard_router
from app.routes.dead_letter import router as dead_letter_router
from app.routes.executions import router as executions_router
from app.services.execution_dispatcher import ExecutionDispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Start Kafka consumer.
    await start_consumer()

    try:
        # 2. Start internal gRPC server.
        grpc_server = await start_grpc_server()

    except Exception:
        await stop_consumer()
        raise

    # 3. Start Kafka lifecycle producer.
    try:
        await start_lifecycle_producer()

    except Exception:
        try:
            await grpc_server.stop(grace=5)
        finally:
            await stop_consumer()
        raise

    # 4. Initialize PostgreSQL-backed dispatcher.
    dispatcher = ExecutionDispatcher()

    # 5. Start background services.
    dispatcher_task = asyncio.create_task(
        dispatcher.run(),
        name="execution-dispatcher",
    )

    consumer_task = asyncio.create_task(
        consume_workflow_triggered(),
        name="kafka-workflow-consumer",
    )

    # 6. Register tasks for health monitoring.
    app.state.consumer_task = consumer_task
    app.state.dispatcher_task = dispatcher_task
    app.state.background_worker_failed = False

    # 7. Detect unexpected background task termination.
    def handle_background_task_done(task: asyncio.Task):
        if task.cancelled():
            return

        try:
            task.exception()
        except asyncio.CancelledError:
            return

        app.state.background_worker_failed = True

    consumer_task.add_done_callback(handle_background_task_done)

    dispatcher_task.add_done_callback(handle_background_task_done)

    try:
        yield

    finally:
        # 8. Stop accepting new Kafka events.
        consumer_task.cancel()

        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

        # 9. Stop dispatching new executions.
        dispatcher_task.cancel()

        try:
            await dispatcher_task
        except asyncio.CancelledError:
            pass

        # 10. Wait for active executions to finish.
        try:
            await dispatcher.shutdown()

        finally:
            # 11. Stop lifecycle producer only after workers finish.
            try:
                await stop_lifecycle_producer()

            finally:
                # 12. Close Kafka consumer.
                try:
                    await stop_consumer()

                finally:
                    # 13. Stop internal gRPC server.
                    await grpc_server.stop(grace=5)


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
app.include_router(executions_router)
app.include_router(dead_letter_router)


@app.get("/health")
async def health(request: Request):
    consumer_task = getattr(
        request.app.state,
        "consumer_task",
        None,
    )

    dispatcher_task = getattr(
        request.app.state,
        "dispatcher_task",
        None,
    )

    background_worker_failed = getattr(
        request.app.state,
        "background_worker_failed",
        False,
    )

    if (
        background_worker_failed
        or consumer_task is None
        or dispatcher_task is None
        or consumer_task.done()
        or dispatcher_task.done()
    ):
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "execution-service",
                "reason": "Background worker unavailable",
            },
        )

    return {
        "status": "ok",
        "service": "execution-service",
    }


app.include_router(dashboard_router)
