"""Atomic fixed-window limits using the service's pooled Redis client."""

import logging
import os
from functools import lru_cache

from fastapi import HTTPException
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# All keys in one call have the same window. Check them all before charging any.
# Redis supplies the clock, so replicas agree on the boundary and retry delay.
_TAKE = """
local now = tonumber(redis.call('TIME')[1])
local window = tonumber(ARGV[1])
local reset = now - now % window + window
for i, key in ipairs(KEYS) do
    if tonumber(redis.call('GET', key) or 0) >= tonumber(ARGV[i + 1]) then
        return {0, reset - now}
    end
end
for _, key in ipairs(KEYS) do
    if redis.call('INCR', key) == 1 then
        redis.call('EXPIREAT', key, reset)
    end
end
return {1, reset}
"""


@lru_cache(maxsize=1)
def client() -> Redis:
    return Redis.from_url(
        os.getenv("RATE_LIMIT_REDIS_URL", "redis://rag-redis:6379/2"),
        socket_connect_timeout=1,
        socket_timeout=1,
        retry=Retry(NoBackoff(), 0),
    )


async def close() -> None:
    if client.cache_info().currsize:
        await client().aclose()
        client.cache_clear()


async def take(window: int, *quotas: tuple[str, int]) -> int:
    """Reserve one request against every quota and return the window's end."""
    keys = [f"relay:ratelimit:{key}" for key, _ in quotas]
    limits = [limit for _, limit in quotas]
    try:
        allowed, value = await client().eval(_TAKE, len(keys), *keys, window, *limits)
    except RedisError:
        logger.warning("Rate limit store unavailable")
        raise HTTPException(
            503, "Rate limit service unavailable", headers={"Retry-After": "1"}
        ) from None
    if not allowed:
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(value)})
    return value
