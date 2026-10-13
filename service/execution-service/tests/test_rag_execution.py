import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest
from app.engine.handlers import rag_search
from app.engine import runner
from app.engine.context import ExecutionContext
from app.engine.step_status import ExecutionStepStatus as Status
from test_execution_components import runner_setup, RunnerSession, FakeAsyncContext

KB = str(uuid4())
VALID = {"knowledge_base_id": KB, "query": "{{trigger.data.question}}", "top_k": 3}
OUTPUT = {"chunks": [{"chunk_id": "c", "content": "policy"}], "context": "policy"}

def graph(query=None):
    config = dict(VALID)
    if query is not None: config["query"] = query
    return ([{"node_id": "t", "node_type": "trigger.webhook"}, {"node_id": "r", "node_type": "ai.rag_search", "configuration": config}], [{"source_node_id": "t", "target_node_id": "r"}])

@pytest.mark.parametrize("failure", [False, True])
def test_handler_closes_channel_and_uses_trusted_workspace(monkeypatch, failure):
    calls = []
    class Client:
        async def retrieve(self, **kw):
            calls.append(kw)
            if failure: raise RuntimeError("timeout")
            return NS(chunks=[NS(chunk_id="c", document_id="d", chunk_index=0, content="policy", score=.81234)])
        async def close(self): calls.append("closed")
    monkeypatch.setattr(rag_search, "RagClient", Client)
    config = {**VALID, "query": "question", "workspace_id": "untrusted"}
    if failure:
        with pytest.raises(RuntimeError): asyncio.run(rag_search.execute_rag_search(config, "trusted"))
    else:
        output = asyncio.run(rag_search.execute_rag_search(config, "trusted"))
        assert output["context"] == "[chunk: c]\npolicy" and output["chunks"][0]["score"] == .8123
    assert calls[0]["workspace_id"] == "trusted" and calls[-1] == "closed"

@pytest.mark.parametrize("patch", [
    {"query": None}, {"query": ""}, {"query": "{{missing}}"}, {"query": "x" * 2001},
    {"top_k": True}, {"top_k": "5"}, {"top_k": 0}, {"top_k": 21}, {"top_k": 1.5},
    {"knowledge_base_id": "bad"}, {"knowledge_base": None},
    {"knowledge_base_id": "", "knowledge_base": KB}, {"knowledge_base_id": None, "knowledge_base": KB},
])
def test_handler_rejects_invalid_configuration_before_rpc(monkeypatch, patch):
    def unexpected(): pytest.fail("RPC client must not be constructed")
    monkeypatch.setattr(rag_search, "RagClient", unexpected)
    with pytest.raises(ValueError):
        asyncio.run(rag_search.execute_rag_search({**VALID, "query": "question", **patch}, "trusted"))

def test_rag_success_resolves_and_persists_output(monkeypatch):
    state = runner_setup(monkeypatch, *graph())
    async def retrieve(configuration, workspace_id):
        assert configuration["query"] == "question" and workspace_id == "tenant"
        return OUTPUT
    monkeypatch.setattr(runner, "execute_rag_search", retrieve)
    result = asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "tenant", {"question": "question"}))
    assert result["context"]["nodes"]["r"] == OUTPUT
    assert state["steps"][-1].output == OUTPUT
    assert all(step.status == Status.COMPLETED for step in state["steps"])

@pytest.mark.parametrize("failure", ["timeout", "resolution", "missing"])
def test_full_lifecycle_failure_closes_active_step(monkeypatch, failure):
    state = runner_setup(monkeypatch, *graph())
    if failure == "timeout":
        async def timeout(**kw): raise RuntimeError("sensitive provider detail")
        monkeypatch.setattr(runner, "execute_rag_search", timeout)
    elif failure == "resolution":
        def broken(self, value): raise ValueError("resolution failed")
        monkeypatch.setattr(runner.ExpressionResolver, "resolve", broken)
    with pytest.raises((RuntimeError, ValueError)):
        asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "tenant", {}))
    assert state["steps"][0].status == Status.COMPLETED
    step = state["steps"][-1]
    assert step.status == Status.FAILED and step.completed_at and step.duration_ms is not None
    assert step.error == {"message": "Node execution failed"}
    assert "trigger" in state["execution"].context

def test_partial_outputs_survive_later_failure(monkeypatch):
    nodes, edges = graph("literal")
    nodes.append({"node_id": "bad", "node_type": "unsupported", "configuration": {}})
    edges.append({"source_node_id": "r", "target_node_id": "bad"})
    state = runner_setup(monkeypatch, nodes, edges)
    async def retrieve(**kw): return OUTPUT
    monkeypatch.setattr(runner, "execute_rag_search", retrieve)
    with pytest.raises(ValueError): asyncio.run(runner.run_execution(state["execution"].id, "w", "v", "tenant"))
    assert state["steps"][1].status == Status.COMPLETED
    assert state["steps"][-1].status == Status.FAILED
    assert state["execution"].context["nodes"]["r"] == OUTPUT

@pytest.mark.parametrize("status", [Status.COMPLETED, Status.WAITING_FOR_APPROVAL, Status.FAILED])
def test_failure_helper_preserves_terminal_and_waiting_steps(monkeypatch, status):
    step = NS(id=uuid4(), status=status)
    state = {"steps": [step]}
    monkeypatch.setattr(runner, "AsyncSessionLocal", lambda: FakeAsyncContext(RunnerSession(state)))
    asyncio.run(runner.mark_step_failed(step.id, "failure"))
    assert step.status == status

def test_restored_context_does_not_mutate_orm_snapshot():
    saved = {"nodes": {"old": {"value": 1}}}
    context = ExecutionContext.from_dict(saved)
    context.set_node_output("new", OUTPUT)
    assert "new" not in saved["nodes"]


def test_graph_error_does_not_overwrite_completed_rag_step(monkeypatch):
    nodes, edges = graph('literal')
    nodes.extend([{'node_id': 'a', 'node_type': 'action.email'}, {'node_id': 'b', 'node_type': 'action.refund'}])
    edges.extend([{'source_node_id': 'r', 'target_node_id': 'a'}, {'source_node_id': 'r', 'target_node_id': 'b'}])
    state = runner_setup(monkeypatch, nodes, edges)
    async def retrieve(**kwargs): return OUTPUT
    monkeypatch.setattr(runner, 'execute_rag_search', retrieve)
    with pytest.raises(ValueError, match='multiple outgoing'):
        asyncio.run(runner.run_execution(state['execution'].id, 'w', 'v', 'tenant'))
    assert state['steps'][-1].status == Status.COMPLETED
    assert state['execution'].context['nodes']['r'] == OUTPUT


def test_output_write_failure_rolls_back_and_fails_active_step(monkeypatch):
    state = runner_setup(monkeypatch, *graph('literal'))
    class WriteFailureSession(RunnerSession):
        async def commit(self):
            if self.state['steps'] and self.state['steps'][-1].node_id == 'r':
                step = self.state['steps'][-1]
                if step.status == Status.COMPLETED and not self.state.get('write_failed'):
                    self.state['write_failed'] = True
                    # Simulate rollback exposing the previously committed RUNNING row.
                    step.status = Status.RUNNING
                    step.output = None
                    raise RuntimeError('database write failed')
        async def rollback(self): self.state['rolled_back'] = True
    monkeypatch.setattr(runner, 'AsyncSessionLocal', lambda: FakeAsyncContext(WriteFailureSession(state)))
    async def retrieve(**kwargs): return OUTPUT
    monkeypatch.setattr(runner, 'execute_rag_search', retrieve)
    with pytest.raises(RuntimeError):
        asyncio.run(runner.run_execution(state['execution'].id, 'w', 'v', 'tenant'))
    assert state['rolled_back']
    assert state['steps'][-1].status == Status.FAILED
    assert state['execution'].context['nodes']['r'] == OUTPUT
