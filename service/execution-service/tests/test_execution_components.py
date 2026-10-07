import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.context import ExecutionContext
from app.engine.executor import SequentialExecutor
from app.engine.graph import ExecutionGraph
from app.engine.resolver import ExpressionResolver
from app.engine.resume import get_resume_state
from app.engine.exceptions import ActionExecutionFailed, HumanApprovalRequired
from app.engine.approval_status import HumanApprovalStatus
from app.engine.step_status import ExecutionStepStatus
from app.engine.status import ExecutionStatus
from app.models.execution import Execution
from app.models.execution_step import ExecutionStep
from app.models.human_approval import HumanApproval
from app.services import approval_service, workflow_service
from app.grpc import action_client, auth_client, workflow_client
from app.kafka import consumer as kafka_consumer
from app.engine import runner
from app.routes import approvals as approval_routes
from app.main import app as execution_app, health, lifespan


def test_context_nested_paths_and_mutations():
    context = ExecutionContext({"email": "a@example.test"})
    context.set_node_output("n1", {"id": 4})
    context.set_node_output("empty", None)
    context.set_variable("count", 2)
    assert context.get("trigger.data.email") == "a@example.test"
    assert context.get("nodes.n1.id") == 4
    assert context.get("variables.count") == 2
    assert context.get("nodes.empty") == {}
    assert context.get("nodes.n1.id.deep") is None
    assert ExecutionContext.from_dict({"x": 1}).to_dict() == {"x": 1}


def test_graph_and_sequential_executor_paths():
    nodes = [
        {"node_id": "t", "node_type": "trigger.manual"},
        {"node_id": "a", "node_type": "action.http_request"},
        {"node_id": "x", "node_type": "transform"},
    ]
    graph = ExecutionGraph(nodes, [
        {"source_node_id": "t", "target_node_id": "a"},
        {"source_node_id": "a", "target_node_id": "x", "condition": "ok"},
    ])
    executor = SequentialExecutor(graph)
    assert [n["node_id"] for n in executor.get_execution_order()] == ["t", "a", "x"]
    assert [n["node_id"] for n in executor.get_action_nodes()] == ["a"]
    assert graph.get_node("missing") is None
    assert graph.get_next_nodes("missing") == []
    assert ExecutionGraph([], []).get_start_node() is None
    with pytest.raises(ValueError, match="start node"):
        SequentialExecutor(ExecutionGraph([], [])).get_execution_order()
    with pytest.raises(ValueError, match="multiple outgoing"):
        SequentialExecutor(ExecutionGraph(nodes[:2], [
            {"source_node_id": "t", "target_node_id": "a"},
            {"source_node_id": "t", "target_node_id": "t"},
        ])).get_execution_order()
    with pytest.raises(ValueError, match="Cycle detected"):
        SequentialExecutor(ExecutionGraph(nodes[:2], [
            {"source_node_id": "t", "target_node_id": "a"},
            {"source_node_id": "a", "target_node_id": "t"},
        ])).get_execution_order()
    with pytest.raises(ValueError, match="Target node not found"):
        SequentialExecutor(ExecutionGraph(nodes[:1], [
            {"source_node_id": "t", "target_node_id": "gone"},
        ])).get_execution_order()


def test_expression_resolver_handles_nested_and_embedded_values():
    context = ExecutionContext({"amount": 12, "customer": {"name": "Ada"}})
    context.set_variable("flag", True)
    resolver = ExpressionResolver(context)
    assert resolver.resolve({
        "number": "{{ trigger.data.amount }}",
        "text": "Hello {{ trigger.data.customer.name }} / {{ missing }}!",
        "items": ["{{ variables.flag }}", 7, "literal"],
        "unknown": "{{ trigger.missing }}",
    }) == {
        "number": 12,
        "text": "Hello Ada / {{ missing }}!",
        "items": [True, 7, "literal"],
        "unknown": None,
    }


class QueryResult:
    def __init__(self, values=(), one=None, first=None):
        self.values, self.one, self.first_value = list(values), one, first
    def scalars(self): return self
    def all(self): return self.values
    def first(self): return self.first_value
    def scalar_one_or_none(self): return self.one


class ApprovalSession:
    def __init__(self, result=None):
        self.result = result or QueryResult()
        self.calls = 0
        self.commits = 0
        self.rollbacks = 0
    async def execute(self, _statement): self.calls += 1; return self.result
    async def commit(self): self.commits += 1
    async def refresh(self, _item): pass
    async def rollback(self): self.rollbacks += 1


def test_approval_service_list_get_approve_reject_and_errors():
    approval = SimpleNamespace(status=HumanApprovalStatus.PENDING, decision=None, decided_at=None)
    session = ApprovalSession(QueryResult([approval], one=approval))
    assert asyncio.run(approval_service.list_pending_approvals("w", "u", session)) == [approval]
    assert asyncio.run(approval_service.get_approval(uuid4(), "w", "u", session)) is approval
    assert asyncio.run(approval_service.approve_approval(uuid4(), "w", "u", session)) is approval
    assert approval.status == HumanApprovalStatus.APPROVED and approval.decision == "approved"
    assert session.commits == 1

    approval.status = HumanApprovalStatus.PENDING
    assert asyncio.run(approval_service.reject_approval(uuid4(), "w", "u", session)) is approval
    assert approval.status == HumanApprovalStatus.REJECTED and approval.decision == "rejected"
    assert session.commits == 2

    missing = ApprovalSession(QueryResult(one=None))
    with pytest.raises(ValueError, match="Approval not found"):
        asyncio.run(approval_service.approve_approval(uuid4(), "w", "u", missing))
    approval.status = HumanApprovalStatus.APPROVED
    with pytest.raises(ValueError, match="already approved"):
        asyncio.run(approval_service.reject_approval(uuid4(), "w", "u", ApprovalSession(QueryResult(one=approval))))

    class BrokenSession(ApprovalSession):
        async def execute(self, _statement): raise RuntimeError("db")
    for fn, args in [
        (approval_service.list_pending_approvals, ("w", "u")),
        (approval_service.get_approval, (uuid4(), "w", "u")),
        (approval_service.approve_approval, (uuid4(), "w", "u")),
        (approval_service.reject_approval, (uuid4(), "w", "u")),
    ]:
        broken = BrokenSession()
        with pytest.raises(RuntimeError, match="db"):
            asyncio.run(fn(*args, broken))
        assert broken.rollbacks == 1



def test_get_resume_state_success_and_failure_paths(monkeypatch):
    execution_id = uuid4()
    step = SimpleNamespace(id=uuid4(), sequence=3)
    approval = SimpleNamespace(execution_step_id=step.id)
    execution = SimpleNamespace(id=execution_id)
    session = SimpleNamespace(get=None, execute=None, rollback=None)
    async def get(_model, _id): return execution
    results = iter([QueryResult([step]), QueryResult(first=approval)])
    async def execute(_statement): return next(results)
    async def rollback(): session.rolled = True
    session.get, session.execute, session.rollback = get, execute, rollback
    results = iter([QueryResult([step]), QueryResult(first=approval)])
    state = asyncio.run(get_resume_state(execution_id, session))
    assert state == (execution, [step], 3)

    async def no_execution(_model, _id): return None
    session.get = no_execution
    with pytest.raises(ValueError, match="Execution not found"):
        asyncio.run(get_resume_state(execution_id, session))

    async def execution_found(_model, _id): return "execution"
    session.get = execution_found
    results = iter([QueryResult([]), QueryResult(first=None)])
    with pytest.raises(ValueError, match="Approved human approval not found"):
        asyncio.run(get_resume_state(execution_id, session))
    results = iter([QueryResult([step]), QueryResult(first=SimpleNamespace(execution_step_id=uuid4()))])
    with pytest.raises(ValueError, match="execution step not found"):
        asyncio.run(get_resume_state(execution_id, session))
    assert session.rolled is True


def test_workflow_service_closes_client(monkeypatch):
    marker = object()
    class Client:
        async def get_workflow_definition(self, **kwargs): self.kwargs = kwargs; return marker
        async def close(self): self.closed = True
    client = Client()
    monkeypatch.setattr(workflow_service, "WorkflowClient", lambda: client)
    assert asyncio.run(workflow_service.load_workflow_definition("w", "v", "x")) is marker
    assert client.closed and client.kwargs == {"workflow_id": "w", "version_id": "v", "workspace_id": "x"}


def test_grpc_client_request_and_close_methods(monkeypatch):
    calls = []
    class Channel:
        async def close(self): calls.append("closed")
    class Stub:
        def __init__(self, _channel): pass
        async def ExecuteAction(self, request): calls.append(request); return "action-result"
        async def GetWorkflowDefinition(self, request): calls.append(request); return "definition"
        async def ValidateWorkflowVersion(self, request): calls.append(request); return "validation"
        async def ValidateToken(self, request): calls.append(request); return "valid"
        async def ResolveWorkspace(self, request): calls.append(request); return "workspace"
    monkeypatch.setattr(action_client.grpc.aio, "insecure_channel", lambda _address: Channel())
    monkeypatch.setattr(action_client.action_pb2_grpc, "ActionInternalServiceStub", Stub)
    ac = action_client.ActionClient()
    assert asyncio.run(ac.execute_action("w", "c", "http", "request")) == "action-result"
    asyncio.run(ac.close())
    monkeypatch.setattr(workflow_client.grpc.aio, "insecure_channel", lambda _address: Channel())
    monkeypatch.setattr(workflow_client.workflow_pb2_grpc, "WorkflowInternalServiceStub", Stub)
    wc = workflow_client.WorkflowClient()
    assert asyncio.run(wc.get_workflow_definition("w", "v", "x")) == "definition"
    assert asyncio.run(wc.validate_workflow_version("w", "v", "x")) == "validation"
    asyncio.run(wc.close())
    monkeypatch.setattr(auth_client.grpc.aio, "insecure_channel", lambda _address: Channel())
    monkeypatch.setattr(auth_client.auth_pb2_grpc, "AuthInternalServiceStub", Stub)
    au = auth_client.AuthGrpcClient()
    assert asyncio.run(au.validate_token("t")) == "valid"
    assert asyncio.run(au.resolve_workspace("u")) == "workspace"
    asyncio.run(au.close())


def test_kafka_consumer_lifecycle_and_message_handling(monkeypatch, capsys):
    seen = []
    class Consumer:
        def __init__(self, *args, **kwargs): seen.append((args, kwargs))
        async def start(self): seen.append("start")
        async def stop(self): seen.append("stop")
        def __aiter__(self): return self
        async def __anext__(self):
            if not hasattr(self, "sent"):
                self.sent = True
                return SimpleNamespace(value=json.dumps({"workflow_id": "w"}).encode())
            if not hasattr(self, "bad"):
                self.bad = True
                return SimpleNamespace(value=b"not-json")
            raise StopAsyncIteration
    monkeypatch.setattr(kafka_consumer, "AIOKafkaConsumer", Consumer)
    async def create(event): seen.append(event); return SimpleNamespace(id="exec")
    monkeypatch.setattr(kafka_consumer, "create_execution", create)
    kafka_consumer.consumer = None
    with pytest.raises(RuntimeError, match="not started"):
        asyncio.run(kafka_consumer.consume_workflow_triggered())
    asyncio.run(kafka_consumer.start_consumer())
    asyncio.run(kafka_consumer.consume_workflow_triggered())
    asyncio.run(kafka_consumer.stop_consumer())
    assert "start" in seen and "stop" in seen and kafka_consumer.consumer is None
    assert any(isinstance(item, dict) for item in seen)
    assert "Failed to process" in capsys.readouterr().out


class RunnerSession:
    def __init__(self, state): self.state = state; self.item = None
    async def __aenter__(self): return self
    async def __aexit__(self, *_args): return False
    def add(self, item):
        item.id = uuid4(); self.item = item; self.state.setdefault("steps", []).append(item)
    async def commit(self): pass
    async def refresh(self, item):
        item.id = item.id or uuid4()
        if item not in self.state.setdefault("steps", []):
            self.state["steps"].append(item)
    async def get(self, model, item_id):
        if model is ExecutionStep:
            if not any(s.id == item_id for s in self.state["steps"]):
                self.state["steps"].append(SimpleNamespace(id=item_id, started_at=None))
            return next(s for s in self.state["steps"] if s.id == item_id)
        if model is Execution: return self.state.setdefault("execution", SimpleNamespace(id=item_id, context={}))


class FakeAsyncContext:
    def __init__(self, session): self.session = session
    async def __aenter__(self): return self.session
    async def __aexit__(self, *_args): return False


def runner_setup(monkeypatch, nodes, edges, action_response=None, execution=None):
    state = {"steps": [], "execution": execution or SimpleNamespace(id=uuid4(), context={})}
    class Workflow:
        async def get_workflow_definition(self, **_kwargs): return SimpleNamespace(nodes_json=json.dumps(nodes), edges_json=json.dumps(edges))
        async def close(self): pass
    class Action:
        async def execute_action(self, **kwargs): state.setdefault("actions", []).append(kwargs); return action_response or SimpleNamespace(success=True, result_json='{"ok": true}', error="")
        async def close(self): pass
    monkeypatch.setattr(runner, "WorkflowClient", Workflow)
    monkeypatch.setattr(runner, "ActionClient", Action)
    monkeypatch.setattr(runner, "AsyncSessionLocal", lambda: FakeAsyncContext(RunnerSession(state)))
    return state


def test_runner_trigger_action_success_resume_and_http_mapping(monkeypatch):
    nodes = [
        {"node_id": "t", "node_type": "trigger.manual"},
        {"node_id": "a", "node_type": "action.http_request", "configuration": {"connection_id": "c", "url": "https://x", "headers": "X: y\ninvalid"}},
    ]
    state = runner_setup(monkeypatch, nodes, [{"source_node_id": "t", "target_node_id": "a"}], SimpleNamespace(success=True, result_json='{"body": {"id": 2}, "status_code": 200}', error=""))
    result = asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "x", {"k": 1}))
    assert len(state["steps"]) == 2
    assert result["context"]["nodes"]["a"]["id"] == 2
    assert state["actions"][0]["provider"] == "http"
    assert state["steps"][0].status == ExecutionStepStatus.COMPLETED
    result2 = asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "x", context_data=result["context"], resume_from_sequence=1))
    assert result2["context"] == result["context"]


def test_runner_missing_connection_unsupported_action_and_failed_action(monkeypatch):
    trigger = {"node_id": "t", "node_type": "trigger.manual"}
    for config, kind, message in [({}, "action.http_request", "connection_id"), ({"connection_id": "c"}, "action.unknown", "Unsupported action")]:
        state = runner_setup(monkeypatch, [trigger, {"node_id": "a", "node_type": kind, "configuration": config}], [{"source_node_id": "t", "target_node_id": "a"}])
        with pytest.raises(ValueError, match=message):
            asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "x"))
    state = runner_setup(monkeypatch, [trigger, {"node_id": "a", "node_type": "action.email", "configuration": {"connection_id": "c"}}], [{"source_node_id": "t", "target_node_id": "a"}], SimpleNamespace(success=False, result_json="", error="mail failed"))
    with pytest.raises(ActionExecutionFailed, match="mail failed"):
        asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "x"))
    assert state["steps"][-1].status == ExecutionStepStatus.FAILED
    assert state["actions"][0]["provider"] == "gmail"


def test_runner_refund_invalid_result_and_missing_execution(monkeypatch):
    nodes = [
        {"node_id": "t", "node_type": "trigger.manual"},
        {"node_id": "r", "node_type": "action.refund", "configuration": {"connection_id": "c"}},
    ]
    response = SimpleNamespace(success=True, result_json='[1, 2]', error="")
    state = runner_setup(monkeypatch, nodes, [{"source_node_id": "t", "target_node_id": "r"}], response)
    result = asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "x"))
    assert state["actions"][0]["provider"] == ""
    assert result["context"]["nodes"]["r"] == {}

    response.result_json = "not-json"
    result = asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "x"))
    assert result["context"]["nodes"]["r"] == {}


def test_runner_human_approval_and_validation_paths(monkeypatch):
    trigger = {"node_id": "t", "node_type": "trigger.manual"}
    approver = str(uuid4())
    node = {"node_id": "h", "node_type": "human.approval", "configuration": {"approver_user_id": approver, "message": "Approve {{ trigger.data.item }}", "timeout_minutes": "5"}}
    execution = SimpleNamespace(id=uuid4(), context={})
    state = runner_setup(monkeypatch, [trigger, node], [{"source_node_id": "t", "target_node_id": "h"}], execution=execution)
    workspace_id = str(uuid4())
    with pytest.raises(HumanApprovalRequired):
        asyncio.run(runner.run_execution(execution.id, "w", "v", workspace_id, {"item": "order"}))
    assert any(step.status == ExecutionStepStatus.WAITING_FOR_APPROVAL for step in state["steps"])
    assert execution.context["trigger"]["data"]["item"] == "order"
    for configuration, message in [({"message": "ok"}, "approver_user_id"), ({"approver_user_id": approver}, "no message")]:
        state = runner_setup(monkeypatch, [trigger, {"node_id": "h", "node_type": "human.approval", "configuration": configuration}], [{"source_node_id": "t", "target_node_id": "h"}])
        with pytest.raises(ValueError, match=message):
            asyncio.run(runner.run_execution(state["execution"].id, "w", "v", workspace_id))


def test_approval_routes_lists_details_approves_rejects_and_maps_errors(monkeypatch):
    now = datetime.now(timezone.utc)
    approval = SimpleNamespace(
        id=uuid4(), execution_id=uuid4(), execution_step_id=uuid4(),
        message="Review", status="pending", decision=None,
        timeout_at=None, created_at=now, updated_at=now,
    )
    identity = {"workspace_id": str(uuid4()), "user_id": str(uuid4())}

    async def list_rows(**_kwargs): return [approval]
    async def get_row(**_kwargs): return approval
    async def approve_row(**_kwargs): return approval
    async def reject_row(**_kwargs): return approval
    monkeypatch.setattr(approval_routes, "list_pending_approvals", list_rows)
    monkeypatch.setattr(approval_routes, "get_approval", get_row)
    monkeypatch.setattr(approval_routes, "approve_approval", approve_row)
    monkeypatch.setattr(approval_routes, "reject_approval", reject_row)

    session = SimpleNamespace(commits=0)
    async def db_get(model, _id):
        if model is Execution:
            return SimpleNamespace(id=approval.execution_id, workflow_id=uuid4(), workflow_version_id=uuid4(), workspace_id=uuid4(), context={})
        return SimpleNamespace(id=approval.execution_step_id, sequence=2, node_id="approval", started_at=None)
    async def commit(): session.commits += 1
    session.get, session.commit = db_get, commit

    listed = asyncio.run(approval_routes.get_approvals(identity, session))
    assert len(listed.approvals) == 1
    assert asyncio.run(approval_routes.get_approval_details(approval.id, identity, session)).id == approval.id
    with pytest.raises(Exception) as caught:
        async def no_row(**_kwargs): return None
        monkeypatch.setattr(approval_routes, "get_approval", no_row)
        awaitable = approval_routes.get_approval_details(approval.id, identity, session)
        asyncio.run(awaitable)
    assert getattr(caught.value, "status_code", None) == 404
    monkeypatch.setattr(approval_routes, "get_approval", get_row)

    async def run(**_kwargs): return None
    monkeypatch.setattr(approval_routes, "run_execution", run)
    response = asyncio.run(approval_routes.approve(approval.id, identity, session))
    assert response.id == approval.id
    assert session.commits == 2
    rejected = asyncio.run(approval_routes.reject(approval.id, identity, session))
    assert rejected.id == approval.id
    assert session.commits == 3

    async def missing_approval(**_kwargs): raise ValueError("Approval not found")
    monkeypatch.setattr(approval_routes, "approve_approval", missing_approval)
    with pytest.raises(Exception) as caught:
        asyncio.run(approval_routes.approve(approval.id, identity, session))
    assert getattr(caught.value, "status_code", None) == 404

    async def conflict(**_kwargs): raise ValueError("Approval is already approved")
    monkeypatch.setattr(approval_routes, "reject_approval", conflict)
    with pytest.raises(Exception) as caught:
        asyncio.run(approval_routes.reject(approval.id, identity, session))
    assert getattr(caught.value, "status_code", None) == 409


def test_approval_route_resume_outcomes_and_missing_records(monkeypatch):
    identity = {"workspace_id": str(uuid4()), "user_id": str(uuid4())}
    now = datetime.now(timezone.utc)
    approval = SimpleNamespace(id=uuid4(), execution_id=uuid4(), execution_step_id=uuid4(), message="x", status="approved", decision="approved", timeout_at=None, created_at=now, updated_at=now)
    execution = SimpleNamespace(id=approval.execution_id, workflow_id=uuid4(), workflow_version_id=uuid4(), workspace_id=uuid4(), context={})
    step = SimpleNamespace(id=approval.execution_step_id, sequence=1, node_id="h", started_at=None)
    session = SimpleNamespace(commits=0)
    async def db_get(model, _id): return execution if model is Execution else step
    async def commit(): session.commits += 1
    session.get, session.commit = db_get, commit
    async def approved(**_kwargs): return approval
    async def run(**_kwargs): raise HumanApprovalRequired("h2")
    monkeypatch.setattr(approval_routes, "approve_approval", approved)
    monkeypatch.setattr(approval_routes, "run_execution", run)
    asyncio.run(approval_routes.approve(approval.id, identity, session))
    assert execution.status == ExecutionStatus.WAITING_FOR_APPROVAL
    assert session.commits == 2

    async def failed(**_kwargs): raise ActionExecutionFailed("a", "bad")
    monkeypatch.setattr(approval_routes, "run_execution", failed)
    asyncio.run(approval_routes.approve(approval.id, identity, session))
    assert execution.status == ExecutionStatus.FAILED and execution.error["node_id"] == "a"

    async def no_execution(_model, _id): return None
    session.get = no_execution
    with pytest.raises(Exception) as caught:
        asyncio.run(approval_routes.approve(approval.id, identity, session))
    assert getattr(caught.value, "status_code", None) == 404


def test_application_health_and_lifespan(monkeypatch):
    assert asyncio.run(health()) == {"status": "ok", "service": "execution-service"}
    assert execution_app.title == "Relay Execution Service"
    calls = []
    async def start(): calls.append("start")
    async def consume():
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            calls.append("cancelled")
            raise
    async def stop(): calls.append("stop")
    monkeypatch.setattr("app.main.start_consumer", start)
    monkeypatch.setattr("app.main.consume_workflow_triggered", consume)
    monkeypatch.setattr("app.main.stop_consumer", stop)

    async def exercise():
        async with lifespan(execution_app):
            await asyncio.sleep(0)
    asyncio.run(exercise())
    assert calls[0] == "start"
    assert set(calls[1:]) == {"cancelled", "stop"}
