from uuid import UUID

from app import rate_limit
from app.config import integer

MANUAL_PER_USER = integer("RATE_LIMIT_MANUAL_PER_USER", 10)
MANUAL_PER_WORKSPACE = integer("RATE_LIMIT_MANUAL_PER_WORKSPACE", 60)
WEBHOOK_PER_HOOK = integer("RATE_LIMIT_WEBHOOK_PER_HOOK", 60)
WEBHOOK_PER_WORKSPACE = integer("RATE_LIMIT_WEBHOOK_PER_WORKSPACE", 300)


async def manual(user_id: str, workspace_id: str) -> None:
    await rate_limit.take(
        60,
        (f"manual:user:{user_id}", MANUAL_PER_USER),
        (f"manual:workspace:{workspace_id}", MANUAL_PER_WORKSPACE),
    )


async def webhook(webhook_id: UUID, workspace_id: UUID) -> None:
    await rate_limit.take(
        60,
        (f"webhook:id:{webhook_id}", WEBHOOK_PER_HOOK),
        (f"webhook:workspace:{workspace_id}", WEBHOOK_PER_WORKSPACE),
    )
