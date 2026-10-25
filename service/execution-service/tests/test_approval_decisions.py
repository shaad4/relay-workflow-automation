"""Approval handoff and decisions on local SQL; external actions are mocked."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from test_execution_history_groups import history
from app.engine import runner
from app.engine.exceptions import HumanApprovalRequired
from app.models.execution_step import ExecutionStep
from app.models.human_approval import HumanApproval
from app.routes import approvals
from app.services import approval_branch_service, execution_queue
from app.services.approval_service import list_pending_approvals


@pytest.fixture
def review(history, monkeypatch):
    session = history["session"]
    session.expire_on_commit = False
    ExecutionStep.__table__.create(history["engine"])
    HumanApproval.__table__.create(history["engine"])
    execution = history["run"](10, status="running")
    execution.completed_at = None
    execution.context = {"trigger": {"data": {}}, "nodes": {"earlier": {"ok": True}}}
    session.commit()
    user = uuid4()
    definition = SimpleNamespace(workflow_name="Review test", nodes_json=json.dumps([
        {"node_id": "review", "node_type": "human.approval", "configuration": {"approver_user_id": str(user), "message": "Review"}},
        {"node_id": "approved-next", "node_type": "action.email", "configuration": {"connection_id": "fake"}},
        {"node_id": "rejected-next", "node_type": "action.email", "configuration": {"connection_id": "fake"}},
    ]), edges_json=json.dumps([
        {"source_node_id": "review", "target_node_id": f"{d}-next", "condition": d} for d in ["approved", "rejected"]
    ]))
    workflow = SimpleNamespace(get_workflow_definition=AsyncMock(return_value=definition), close=AsyncMock())
    monkeypatch.setattr(runner, "WorkflowClient", lambda: workflow)
    monkeypatch.setattr(approval_branch_service, "WorkflowClient", lambda: workflow)
    action = SimpleNamespace(execute_action=AsyncMock(), close=AsyncMock())
    monkeypatch.setattr(runner, "ActionClient", lambda: action)
    snapshots, retained = [], []
    class Adapter:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return False
        async def execute(self, statement): return session.execute(statement)
        async def get(self, model, item_id): return session.get(model, item_id)
        def add(self, item):
            retained.append(item)
            session.add(item)
        async def commit(self):
            session.commit()
            rows = session.execute(select(HumanApproval)).scalars().all()
            if rows: snapshots.append((execution.status, [row.status for row in rows]))
        async def rollback(self): session.rollback()
        async def refresh(self, item): session.refresh(item)
    adapter = Adapter()
    monkeypatch.setattr(runner, "AsyncSessionLocal", lambda: adapter)
    monkeypatch.setattr(execution_queue, "AsyncSessionLocal", lambda: adapter)
    identity = {"workspace_id": str(history["workspace"]), "user_id": str(user)}
    async def current_identity(): return identity
    async def db(): return adapter
    app = FastAPI()
    app.include_router(approvals.router)
    app.dependency_overrides[approvals.get_current_identity] = current_identity
    app.dependency_overrides[approvals.get_db] = db
    return SimpleNamespace(**locals())


async def pause(review):
    with pytest.raises(HumanApprovalRequired):
        await runner.run_execution(review.execution.id, str(review.execution.workflow_id),
            str(review.execution.workflow_version_id), review.identity["workspace_id"],
            context_data=review.execution.context, start_node_id="review")
    approval = review.session.execute(select(HumanApproval)).scalar_one()
    assert review.snapshots == [("waiting_for_approval", ["pending"])]
    assert review.execution.claimed_by is None and review.execution.lease_expires_at is None
    review.action.execute_action.assert_not_awaited()
    return approval


@pytest.mark.parametrize("decision", ["approved", "rejected"])
@pytest.mark.parametrize("connected", [True, False])
def test_decision_leaves_inbox_and_queues_exact_branch(review, monkeypatch, decision, connected):
    if not connected:
        review.definition.edges_json = json.dumps([e for e in json.loads(review.definition.edges_json) if e["condition"] != decision])
    async def check():
        approval = await pause(review)
        async with AsyncClient(transport=ASGITransport(app=review.app), base_url="http://test") as client:
            endpoint = "approve" if decision == "approved" else "reject"
            response = await client.post(f"/approvals/{approval.id}/{endpoint}/")
            assert response.status_code == 200, response.text
            assert response.json()["status"] == decision
            assert await list_pending_approvals(review.history["workspace"], review.user, review.adapter) == []
            assert review.execution.status == "pending"
            checkpoint = review.execution.context["_resume"]
            assert checkpoint["decision"] == decision
            assert checkpoint["start_node_id"] == (f"{decision}-next" if connected else None)
            assert review.execution.context["nodes"]["earlier"] == {"ok": True}
            duplicate = await client.post(f"/approvals/{approval.id}/{endpoint}/")
            assert duplicate.status_code == 409
            assert duplicate.json()["detail"] == f"Approval is already {decision}"
        async def claim(**kwargs):
            review.execution.status = "running"
            review.execution.claimed_by = kwargs["worker_id"]
            return True
        run = AsyncMock(return_value={"context": {"nodes": {"earlier": {"ok": True}}}})
        finalize = AsyncMock(return_value="completed")
        monkeypatch.setattr(execution_queue, "claim_pending_execution", claim)
        monkeypatch.setattr(execution_queue, "execution_heartbeat", AsyncMock())
        monkeypatch.setattr(execution_queue, "publish_execution_lifecycle", AsyncMock())
        monkeypatch.setattr(execution_queue, "run_execution", run)
        monkeypatch.setattr(execution_queue, "finalize_execution", finalize)
        assert await execution_queue.execute_pending_execution(review.execution.id)
        assert run.await_count == int(connected)
        if connected:
            assert run.call_args.kwargs["start_node_id"] == f"{decision}-next"
            assert "_resume" not in run.call_args.kwargs["context_data"]
        assert finalize.call_args.kwargs["status"] == "completed"
    asyncio.run(check())


@pytest.mark.parametrize("state", ["running", "failed", "completed", "cancelled"])
def test_inconsistent_execution_is_not_resumed_and_conflict_is_explicit(review, state):
    async def check():
        approval = await pause(review)
        review.execution.status = state
        review.session.commit()
        async with AsyncClient(transport=ASGITransport(app=review.app), base_url="http://test") as client:
            for endpoint in ["approve", "reject"]:
                response = await client.post(f"/approvals/{approval.id}/{endpoint}/")
                assert response.status_code == 409
                assert response.json()["detail"] == "Execution is not waiting for approval"
                assert review.session.get(HumanApproval, approval.id).status == "pending"
                assert "_resume" not in review.execution.context
    asyncio.run(check())


@pytest.mark.parametrize("fast_decision", [False, True])
def test_queue_does_not_finalize_over_atomic_handoff(review, monkeypatch, fast_decision):
    async def claim(**kwargs):
        review.execution.claimed_by = kwargs["worker_id"]
        return True
    async def run(**kwargs):
        kwargs["start_node_id"] = "review"
        try:
            return await runner.run_execution(**kwargs)
        except HumanApprovalRequired:
            if fast_decision:
                approval = review.session.execute(select(HumanApproval)).scalar_one()
                await approvals.approve(approval.id, review.identity, review.adapter)
            raise
    finalize = AsyncMock()
    monkeypatch.setattr(execution_queue, "claim_pending_execution", claim)
    monkeypatch.setattr(execution_queue, "execution_heartbeat", AsyncMock())
    monkeypatch.setattr(execution_queue, "publish_execution_lifecycle", AsyncMock())
    monkeypatch.setattr(execution_queue, "run_execution", run)
    monkeypatch.setattr(execution_queue, "finalize_execution", finalize)
    assert asyncio.run(execution_queue.execute_pending_execution(review.execution.id))
    assert review.execution.status == ("pending" if fast_decision else "waiting_for_approval")
    finalize.assert_not_awaited()


@pytest.mark.parametrize("field", ["workspace_id", "user_id"])
def test_other_workspace_or_approver_cannot_decide(review, field):
    async def check():
        approval = await pause(review)
        review.identity[field] = str(uuid4())
        async with AsyncClient(transport=ASGITransport(app=review.app), base_url="http://test") as client:
            for endpoint in ["approve", "reject"]:
                response = await client.post(f"/approvals/{approval.id}/{endpoint}/")
                assert response.status_code == 404
        assert review.session.get(HumanApproval, approval.id).status == "pending"
    asyncio.run(check())


@pytest.mark.parametrize("conditions", [["approved", "approved"], ["invalid"]])
def test_malformed_branches_do_not_record_decision(review, conditions):
    review.definition.edges_json = json.dumps([
        {"source_node_id": "review", "target_node_id": "approved-next", "condition": condition}
        for condition in conditions
    ])
    async def check():
        approval = await pause(review)
        async with AsyncClient(transport=ASGITransport(app=review.app), base_url="http://test") as client:
            response = await client.post(f"/approvals/{approval.id}/approve/")
            assert response.status_code == 409
            assert response.json()["detail"] == "Invalid human approval branch configuration"
        assert review.session.get(HumanApproval, approval.id).status == "pending"
        assert review.execution.status == "waiting_for_approval"
    asyncio.run(check())


def test_cancellation_at_handoff_does_not_publish_pending_approval(review):
    from datetime import datetime, timezone
    from app.engine.exceptions import ExecutionCancellationRequested
    execute = review.adapter.execute
    async def cancel_before_lock(statement):
        if getattr(statement, "_for_update_arg", None) is not None:
            review.execution.cancel_requested_at = datetime.now(timezone.utc)
            review.session.commit()
        return await execute(statement)
    review.adapter.execute = cancel_before_lock
    async def check():
        with pytest.raises(ExecutionCancellationRequested):
            await runner.run_execution(review.execution.id, str(review.execution.workflow_id),
                str(review.execution.workflow_version_id), review.identity["workspace_id"], start_node_id="review")
        assert review.session.execute(select(HumanApproval)).scalars().all() == []
        assert review.execution.status == "running"
        review.action.execute_action.assert_not_awaited()
    asyncio.run(check())
