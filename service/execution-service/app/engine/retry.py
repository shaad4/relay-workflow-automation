import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.engine.exceptions import ActionExecutionFailed


T = TypeVar("T")

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 10

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
SAFE_HTTP_METHODS = {"GET", "HEAD"}


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    node_id: str,
    method: str,
) -> tuple[T, int]:
    """
    Retry safe HTTP operations on temporary failures.

    Returns:
        (result, attempts_used)
    """

    safe_method = method.upper() in SAFE_HTTP_METHODS

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await operation()
            return result, attempt

        except ActionExecutionFailed as exc:
            should_retry = (
                safe_method
                and exc.retryable
                and attempt < MAX_ATTEMPTS
            )

            if not should_retry:
                raise

            delay = min(
                BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
                MAX_DELAY_SECONDS,
            )

            # Small jitter prevents simultaneous retries.
            delay += random.uniform(0, 0.5)

            await asyncio.sleep(delay)

    raise RuntimeError(
        f"Retry loop unexpectedly exhausted for {node_id}"
    )
