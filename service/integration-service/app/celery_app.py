import os

from celery import Celery

from app.config import validate_startup

validate_startup()

REDIS_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://rag-redis:6379/1",
)


celery_app = Celery(
    "relay_integration",
    broker=REDIS_URL,
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    task_default_queue="integration",
    imports=("app.tasks.schedule_tasks",),
    beat_schedule={
        "check-due-workflow-schedules": {
            "task": "integration.check_due_schedules",
            "schedule": 60.0,
        },
    },
)
