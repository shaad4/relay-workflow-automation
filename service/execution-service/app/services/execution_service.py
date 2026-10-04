from datetime import datetime, timezone
from uuid import UUID

from app.db.database import AsyncSessionLocal
from app.models.execution import Execution


async def create_execution(event: dict) -> Execution:
    async with AsyncSessionLocal() as session:
        try:
            execution = Execution(
                workspace_id=UUID(event["workspace_id"]),
                workflow_id=UUID(event["workflow_id"]),
                workflow_version_id=UUID(event["workflow_version_id"]),
                status="pending",
                trigger_type=event["event_type"],
                trigger_data=event.get("payload"),
                context={},
                started_at=datetime.now(timezone.utc),
            )

            session.add(execution)

            await session.commit()
            await session.refresh(execution)

            return execution

        except Exception:
            await session.rollback()
            raise