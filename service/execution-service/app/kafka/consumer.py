import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer, TopicPartition

from app.services.execution_queue import (
    create_pending_execution,
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

KAFKA_TOPIC = "workflow.triggered"
KAFKA_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID", "execution-service")

consumer: AIOKafkaConsumer | None = None


async def start_consumer():
    global consumer

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )

    await consumer.start()


async def stop_consumer():
    global consumer

    if consumer is not None:
        await consumer.stop()
        consumer = None


async def consume_workflow_triggered():
    """
    Persist Kafka events before acknowledging them.

    Workflow execution is handled separately by
    the PostgreSQL-backed ExecutionDispatcher.
    """

    if consumer is None:
        raise RuntimeError("Kafka consumer is not started")

    async for message in consumer:
        try:
            event = json.loads(message.value.decode("utf-8"))

            if not isinstance(event, dict):
                raise ValueError("Kafka event must be a JSON object")

            # Persist execution + idempotency key atomically.
            await create_pending_execution(event)

            # Commit the next offset only after DB commit.
            partition = TopicPartition(
                message.topic,
                message.partition,
            )

            await consumer.commit(
                {
                    partition: message.offset + 1,
                }
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            # Do not acknowledge an event that failed
            # durable persistence or validation.
            # Stop consuming to prevent advancing past it.
            raise
