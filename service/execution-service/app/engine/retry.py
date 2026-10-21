import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.engine.exceptions import ActionExecutionFailed
from app.ai.exceptions import (
    AIRateLimitError,
    AITimeoutError,
    AIServiceUnavailableError,
)


T = TypeVar("T")

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 2
MAX_DELAY_SECONDS = 10

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
SAFE_HTTP_METHODS = {"GET", "HEAD"}

RETRYABLE_AI_ERRORS = (
    AIRateLimitError,
    AITimeoutError,
    AIServiceUnavailableError,
)


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    node_id: str,
    method: str | None = None,
) -> tuple[T, int]:
    """
    Retry safe HTTP and temporary AI failures.

    Returns:
        (result, attempts_used)
    """

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await operation()
            return result, attempt

        except (
            ActionExecutionFailed,
            *RETRYABLE_AI_ERRORS,
        ) as exc:

            if isinstance(exc, ActionExecutionFailed):
                should_retry = (
                    method is not None
                    and method.upper() in SAFE_HTTP_METHODS
                    and exc.retryable
                )
            else:
                should_retry = True

            if not should_retry or attempt >= MAX_ATTEMPTS:
                exc.attempts_used = attempt
                raise

            delay = min(
                BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
                MAX_DELAY_SECONDS,
            )

            delay += random.uniform(0, 0.5)

            await asyncio.sleep(delay)

    raise RuntimeError(
        f"Retry loop unexpectedly exhausted for {node_id}"
    )
