import asyncio
import os
from uuid import uuid4

import pytest
from app import rate_limit
from app.services import trigger_limits
from fastapi import HTTPException


@pytest.mark.parametrize("trigger", ["manual", "webhook"])
async def test_workspace_quota_is_atomic_and_isolated(trigger, monkeypatch):
    url = os.getenv("RATE_LIMIT_TEST_REDIS_URL")
    if not url:
        pytest.skip("Set RATE_LIMIT_TEST_REDIS_URL to run real Redis checks")
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", url)
    setter = getattr(trigger_limits, trigger)
    monkeypatch.setattr(trigger_limits, trigger.upper() + "_PER_WORKSPACE", 1)
    first, second = uuid4(), uuid4()
    workspace = uuid4()
    try:
        seconds, _ = await rate_limit.client().time()
        if seconds % 60 >= 58:
            await asyncio.sleep(2)
        await setter(first, workspace)
        with pytest.raises(HTTPException) as exc:
            await setter(second, workspace)
        assert exc.value.status_code == 429 and int(exc.value.headers["Retry-After"]) > 0
        await setter(second, uuid4())
    finally:
        await rate_limit.close()
