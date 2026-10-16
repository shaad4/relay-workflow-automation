from app.celery_app import celery_app


@celery_app.task(name="integration.check_due_schedules")
def check_due_schedules():
    """Placeholder for scheduled workflow dispatch."""
    return None