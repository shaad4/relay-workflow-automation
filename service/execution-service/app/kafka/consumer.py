import json
import os

from aiokafka import AIOKafkaConsumer


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

KAFKA_TOPIC = "workflow.triggered"
KAFKA_GROUP_ID = "execution-service"


consumer: AIOKafkaConsumer | None = None


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


async def consume_workflow_triggered():
    if consumer is None:
        raise RuntimeError("Kafka consumer is not started")

    async for message in consumer:
        event = json.loads(message.value.decode("utf-8"))

        print(
            "Received workflow.triggered event:",
            event,
        )