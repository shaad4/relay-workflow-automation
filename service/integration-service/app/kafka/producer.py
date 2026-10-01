import json
import os

from aiokafka import AIOKafkaProducer

from app.schemas.events import WorkflowTriggeredEvent


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)


producer: AIOKafkaProducer | None = None


async def start_producer():
    global producer

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    )

    await producer.start()


async def stop_producer():
    global producer

    if producer is not None:
        await producer.stop()
        producer = None


async def publish_workflow_triggered(
    event: WorkflowTriggeredEvent,
):
    if producer is None:
        raise RuntimeError("Kafka producer is not started")

    message = event.model_dump(mode="json")

    await producer.send_and_wait(
        "workflow.triggered",
        json.dumps(message).encode("utf-8"),
    )