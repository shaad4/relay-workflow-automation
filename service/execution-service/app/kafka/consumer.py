
import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer

from app.services.execution_service import create_execution


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

KAFKA_TOPIC = "workflow.triggered"
KAFKA_GROUP_ID = "execution-service"

EXECUTION_MAX_CONCURRENCY = int(
    os.getenv("EXECUTION_MAX_CONCURRENCY", "5")
)

if EXECUTION_MAX_CONCURRENCY < 1:
    raise ValueError(
        "EXECUTION_MAX_CONCURRENCY must be at least 1"
    )


consumer: AIOKafkaConsumer | None = None

active_tasks: set[asyncio.Task] = set()

execution_semaphore = asyncio.Semaphore(
    EXECUTION_MAX_CONCURRENCY
)


async def start_consumer():
    global consumer

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()


async def stop_consumer():
    global consumer

    if consumer is not None:
        await consumer.stop()
        consumer = None


async def process_workflow_event(event: dict):
    """
    Process one workflow execution.

    The semaphore slot is released after
    execution finishes or fails.
    """

    try:
        execution = await create_execution(event)

        print(
            "Execution finished:",
            execution.id,
            flush=True,
        )

    except asyncio.CancelledError:
        raise

    except Exception:
        print(
            "Failed to process workflow.triggered event",
            flush=True,
        )

    finally:
        execution_semaphore.release()


async def consume_workflow_triggered():
    """
    Consume Kafka events with bounded concurrency.

    Each workflow runs in its own asyncio task.
    """

    if consumer is None:
        raise RuntimeError(
            "Kafka consumer is not started"
        )

    try:
        async for message in consumer:

            # Wait for an available execution slot.
            await execution_semaphore.acquire()

            try:
                event = json.loads(
                    message.value.decode("utf-8")
                )

                if not isinstance(event, dict):
                    raise ValueError(
                        "Kafka event must be a JSON object"
                    )

                task = asyncio.create_task(
                    process_workflow_event(event)
                )

                active_tasks.add(task)

                task.add_done_callback(
                    active_tasks.discard
                )

            except asyncio.CancelledError:
                execution_semaphore.release()
                raise

            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                execution_semaphore.release()

                print(
                    "Invalid workflow.triggered event",
                    flush=True,
                )

            except Exception:
                execution_semaphore.release()

                print(
                    "Unable to dispatch workflow execution",
                    flush=True,
                )

    except asyncio.CancelledError:
        raise


async def wait_for_active_executions():
    """
    Wait for running workflows to finish
    before shutting down dependencies.
    """

    if active_tasks:
        await asyncio.gather(
            *list(active_tasks),
            return_exceptions=True,
        )
