"""Cancellation reads against local SQL fixtures; no external actions."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from test_execution_history_groups import history, SessionAdapter
from app.models.human_approval import HumanApproval
from app.routes import approvals
from app.schemas.executions import ExecutionDetailResponse
from app.services.approval_service import list_pending_approvals


def test_approval_filter_preserves_workspace_and_approver_scope(history):
    HumanApproval.__table__.create(history["engine"])
    session = history["session"]
    user, other_user = uuid4(), uuid4()
    workspace = history["workspace"]
    rows = []
    for status, owner, tenant in [
        ("pending", user, workspace), ("cancelled", user, workspace),
        ("cancelled", other_user, workspace),
        ("cancelled", user, history["other_workspace"]),
    ]:
        row = HumanApproval(id=uuid4(), execution_id=history["original"].id,
                            execution_step_id=uuid4(), workspace_id=tenant,
                            approver_user_id=owner, message="Review", status=status)
        session.add(row)
        rows.append(row)
    session.commit()
    adapter = SessionAdapter(session)
    pending = asyncio.run(list_pending_approvals(workspace, user, adapter))
    cancelled = asyncio.run(list_pending_approvals(workspace, user, adapter, status="cancelled"))
    assert [row.id for row in pending] == [rows[0].id]
    assert [row.id for row in cancelled] == [rows[1].id]


def test_detail_cancellation_timestamp_and_workspace_scope(history):
    execution = history["original"]
    execution.cancel_requested_at = datetime.now(timezone.utc)
    history["session"].commit()
    # Isolate this read contract from the existing unavailable lineage helpers.
    history["service"].repository.get_execution_lineage = AsyncMock(return_value={})
    history["service"].repository.get_recovery_events = AsyncMock(return_value={})
    result = asyncio.run(history["service"].get_execution_by_id(execution.id, history["workspace"]))
    assert ExecutionDetailResponse.model_validate(result).cancel_requested_at == execution.cancel_requested_at
    assert asyncio.run(history["service"].get_execution_by_id(execution.id, history["other_workspace"])) is None


def test_approval_route_status_validation_and_default(monkeypatch):
    app = FastAPI()
    app.include_router(approvals.router)
    identity = {"workspace_id": str(uuid4()), "user_id": str(uuid4())}
    async def current_identity(): return identity
    async def db(): return None
    app.dependency_overrides[approvals.get_current_identity] = current_identity
    app.dependency_overrides[approvals.get_db] = db
    query = AsyncMock(return_value=[])
    monkeypatch.setattr(approvals, "list_pending_approvals", query)
    async def check():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/approvals/")).status_code == 200
            assert query.call_args.kwargs["status"] == "pending"
            assert (await client.get("/approvals/?status=cancelled")).status_code == 200
            assert query.call_args.kwargs["status"] == "cancelled"
            assert query.call_args.kwargs["workspace_id"] == identity["workspace_id"]
            assert query.call_args.kwargs["approver_user_id"] == identity["user_id"]
            assert (await client.get("/approvals/?status=invalid")).status_code == 422
    asyncio.run(check())


def test_cancel_endpoint_statuses_and_workspace_identity(monkeypatch):
    from app.routes import executions
    app = FastAPI()
    app.include_router(executions.router)
    identity = {"workspace_id": str(uuid4()), "user_id": str(uuid4())}
    async def current_identity(): return identity
    async def db(): return None
    app.dependency_overrides[executions.get_current_identity] = current_identity
    app.dependency_overrides[executions.get_db] = db
    cancel = AsyncMock()
    monkeypatch.setattr(executions.ExecutionCancellationService, "cancel_execution", cancel)
    execution_id = uuid4()
    async def check():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for status, code in [("cancelled", 200), ("cancellation_requested", 200),
                                 ("already_cancelled", 200), (None, 404), ("not_cancellable", 409)]:
                cancel.return_value = status
                response = await client.post(f"/executions/{execution_id}/cancel/")
                assert response.status_code == code
                assert str(cancel.call_args.kwargs["workspace_id"]) == identity["workspace_id"]
                assert cancel.call_args.kwargs["execution_id"] == execution_id
                if code == 200:
                    assert response.json()["status"] == status
    asyncio.run(check())
