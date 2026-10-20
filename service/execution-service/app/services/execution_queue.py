from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.db.database import AsyncSessionLocal
from app.repositories.execution_queue import ExecutionQueueRepository


async def create_pending_execution(event: dict) -> UUID:
    """
    Atomically create a pending execution and idempotency key.

    Returns the execution ID.

    Duplicate events return the existing execution ID.
    No workflow is executed here.
    """

    # 1. Validate required event identifiers.
    try:
        event_id = UUID(str(event["event_id"]))
        workspace_id = UUID(str(event["workspace_id"]))
        workflow_id = UUID(str(event["workflow_id"]))
        workflow_version_id = UUID(
            str(event["workflow_version_id"])
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid workflow event identifiers"
        ) from exc

    # 2. Validate trigger type.
    trigger_type = event.get("trigger_type")

    if trigger_type not in {
        "webhook",
        "manual",
        "schedule",
    }:
        raise ValueError(
            "Invalid workflow trigger type"
        )

    # 3. Validate payload.
    trigger_data = event.get("payload", {})

    if not isinstance(trigger_data, dict):
        raise ValueError(
            "Workflow event payload must be an object"
        )

    # 4. Generate a stable idempotency key.
    event_key = f"workflow.triggered:{event_id}"

    # 5. Atomically insert execution and key.
    async with AsyncSessionLocal() as session:
        repository = ExecutionQueueRepository(session)

        try:
            execution = await repository.create_pending(
                workspace_id=workspace_id,
                workflow_id=workflow_id,
                workflow_version_id=workflow_version_id,
                trigger_type=trigger_type,
                trigger_data=trigger_data,
                event_key=event_key,
            )

            execution_id = execution.id

            await session.commit()

            return execution_id

        except IntegrityError:
            await session.rollback()

            # A duplicate event may already have an execution.
            existing = await repository.get_by_event_key(
                workspace_id=workspace_id,
                key=event_key,
            )

            if existing is not None:
                return existing.id

            # The integrity failure was unrelated to this event key.
            raise

        except Exception:
            await session.rollback()
            raise
