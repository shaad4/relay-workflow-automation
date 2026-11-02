import os

from celery import Celery

from app.config import validate_startup

validate_startup()

REDIS_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://rag-redis:6379/0",
)


celery_app = Celery(
    "relay_rag",
    broker=REDIS_URL,
    include=["app.tasks.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_default_queue="rag_ingestion",
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
