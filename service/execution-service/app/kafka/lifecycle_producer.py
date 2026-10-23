import json
import os

from aiokafka import AIOKafkaProducer

from app.schemas.lifecycle_events import WorkflowLifecycleEvent


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

producer: AIOKafkaProducer | None = None


async def start_lifecycle_producer():
    global producer

    if producer is not None:
        return

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    )

    try:
        await producer.start()
    except Exception:
        producer = None
        raise


async def stop_lifecycle_producer():
    global producer

    if producer is not None:
        try:
            await producer.stop()
        finally:
            producer = None


async def publish_lifecycle_event(
    event: WorkflowLifecycleEvent,
) -> bool:
    """
    Publish a workflow lifecycle event.

    Returns True on successful Kafka acknowledgment.
    Returns False if publishing fails.
    """

    if producer is None:
        return False

    try:
        message = event.model_dump(mode="json")

        await producer.send_and_wait(
            topic=event.event_type,
            value=json.dumps(message).encode("utf-8"),
            key=str(event.execution_id).encode("utf-8"),
        )

        return True

    except Exception:
        return False
