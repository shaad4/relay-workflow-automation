import os

from aiokafka import AIOKafkaProducer


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

