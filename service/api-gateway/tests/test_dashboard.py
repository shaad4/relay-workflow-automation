import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.routes.dashboard import overview as dashboard


def execution_data():
    return dict(
        range="7d",
        timezone="UTC",
        window_start="2026-10-18T00:00:00Z",
        window_end="2026-10-24T12:00:00Z",
        total_executions=0,
        completed=0,
        failed=0,
        running=0,
        waiting_for_approval=0,
        pending=0,
        cancelled=0,
        success_rate=None,
        pending_approvals=0,
        pending_dlq=0,
        execution_activity=[],
        recent_executions=[],
        context="must not leak",
    )


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("ok", 200),
        ("timeout", 504),
        ("network", 502),
        ("500", 502),
        ("401", 401),
        ("malformed", 502),
        ("invalid-range", 422),
    ],
)
def test_gateway_aggregation_and_safe_errors(monkeypatch, failure, expected):
    client = AsyncMock()
    client.__aenter__.return_value = client

    async def get(url, **kwargs):
        assert kwargs["headers"] == {"Authorization": "Bearer validated-token"}
        assert "workspace_id" not in kwargs.get("params", {})
        if failure == "timeout":
            raise httpx.ReadTimeout("internal URL")
        if failure == "network":
            raise httpx.ConnectError("internal URL")
        if failure in ("500", "401"):
            return httpx.Response(int(failure), json={"detail": "private stack"})
        if failure == "malformed":
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json=execution_data()
            if url == dashboard.EXECUTION_URL
            else {"total_workflows": 3, "active_workflows": 2},
        )

    client.get.side_effect = get
    real_client = httpx.AsyncClient
    monkeypatch.setattr(dashboard.httpx, "AsyncClient", lambda **kwargs: client)
    app = FastAPI()
    app.include_router(dashboard.router)
    app.dependency_overrides[dashboard.get_current_identity] = lambda: {
        "workspace_id": "trusted",
        "user_id": "trusted",
    }

    async def check():
        async with real_client(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            cookies={"relay_access_token": "validated-token"},
        ) as caller:
            result = await caller.get(
                "/dashboard/overview?range="
                + ("bad" if failure == "invalid-range" else "7d")
                + "&workspace_id=attacker",
                headers={"x-workspace-id": "attacker"},
            )
        assert result.status_code == expected
        assert "private" not in result.text and "internal URL" not in result.text
        if expected == 200:
            assert result.json()["active_workflows"] == 2 and result.json()["total_executions"] == 0
            assert "context" not in result.json()
        if expected == 422:
            client.get.assert_not_called()

    asyncio.run(check())
