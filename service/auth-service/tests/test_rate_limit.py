import asyncio
import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app import rate_limit
from app.services import auth_limits
from fastapi import HTTPException
from redis.exceptions import ConnectionError


@pytest.fixture
async def redis_store(monkeypatch):
    url = os.getenv("RATE_LIMIT_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set RATE_LIMIT_TEST_REDIS_URL to run real Redis checks")
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", url)
    try:
        yield rate_limit.client()
    finally:
        await rate_limit.close()


async def test_atomic_limits_under_concurrency(redis_store):
    tenant = str(uuid4())
    user = str(uuid4())
    # Avoid starting an assertion on opposite sides of the hour boundary.
    seconds, _ = await redis_store.time()
    if seconds % 3600 >= 3598:
        await asyncio.sleep(2)
    results = await asyncio.gather(
        *(rate_limit.take(3600, (user, 5), (tenant, 10)) for _ in range(20)),
        return_exceptions=True,
    )
    assert sum(isinstance(result, int) for result in results) == 5
    errors = [result for result in results if isinstance(result, HTTPException)]
    assert len(errors) == 15
    assert all(e.status_code == 429 and 1 <= int(e.headers["Retry-After"]) <= 3600 for e in errors)
    assert await redis_store.get("relay:ratelimit:" + tenant) == b"5"
    assert 0 < await redis_store.ttl("relay:ratelimit:" + user) <= 3600
    await rate_limit.take(3600, (str(uuid4()), 5), (tenant, 10))


async def test_login_reservation_and_expiry(redis_store):
    key = auth_limits.account_key("login", str(uuid4()) + "@example.com")
    reset = await rate_limit.take(1, (key, 1))
    await auth_limits.release(key, reset)
    await rate_limit.take(1, (key, 1))
    await asyncio.sleep(1.05)
    await rate_limit.take(900, (key, 1))
    await auth_limits.release(key, reset)
    with pytest.raises(HTTPException) as blocked:
        await rate_limit.take(900, (key, 1))
    assert blocked.value.status_code == 429


async def test_redis_outage_is_distinct_from_exhausted_quota(monkeypatch):
    store = AsyncMock()
    store.eval.side_effect = ConnectionError()
    monkeypatch.setattr(rate_limit, "client", lambda: store)
    with pytest.raises(HTTPException) as exc:
        await rate_limit.take(60, ("test", 1))
    assert exc.value.status_code == 503


def test_email_keys_are_normalized_private_and_scoped():
    key = auth_limits.account_key("login", " Test@Example.COM ")
    assert key == auth_limits.account_key("login", "test@example.com")
    assert "example" not in key
    assert key != auth_limits.account_key("verification", "test@example.com")
