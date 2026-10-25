import asyncio
import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import grpc
import pytest
from sqlalchemy.dialects import sqlite

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.grpc import execution_server
from app.grpc.generated.execution import approval_lifecycle_pb2 as messages
from app.grpc.generated.execution import approval_lifecycle_pb2_grpc as rpc


def test_workflow_client_deletes_only_matching_approvals_over_grpc(monkeypatch):
    async def exercise():
        workflow, other_workflow, workspace, other_workspace = [uuid4() for _ in range(4)]
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE executions (id TEXT, workflow_id TEXT, workspace_id TEXT)")
        db.execute("CREATE TABLE human_approvals (id TEXT, execution_id TEXT, workspace_id TEXT)")
        for index, (wf, ws) in enumerate(
            [
                (workflow, workspace),
                (workflow, workspace),
                (other_workflow, workspace),
                (workflow, other_workspace),
            ]
        ):
            execution = uuid4().hex
            db.execute("INSERT INTO executions VALUES (?, ?, ?)", (execution, wf.hex, ws.hex))
            db.execute(
                "INSERT INTO human_approvals VALUES (?, ?, ?)", (str(index), execution, ws.hex)
            )

        async def execute(statement):
            sql = str(
                statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
            )
            return SimpleNamespace(rowcount=db.execute(sql).rowcount)

        session = AsyncMock()
        session.execute.side_effect = execute
        session.__aenter__.return_value = session
        monkeypatch.setattr(execution_server, "AsyncSessionLocal", lambda: session)
        server = grpc.aio.server()
        rpc.add_ExecutionInternalServiceServicer_to_server(
            execution_server.ExecutionInternalService(), server
        )
        port = server.add_insecure_port("127.0.0.1:0")
        await server.start()

        client_path = (
            Path(__file__).resolve().parents[2] / "workflow-service/app/grpc/execution_client.py"
        )
        spec = importlib.util.spec_from_file_location("workflow_execution_client", client_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monkeypatch.setattr(module, "EXECUTION_GRPC_URL", f"127.0.0.1:{port}")
        client = module.ExecutionGrpcClient()
        try:
            assert await client.delete_workflow_approvals(workflow, workspace) == 2
            assert db.execute("SELECT id FROM human_approvals ORDER BY id").fetchall() == [
                ("2",),
                ("3",),
            ]
            assert await client.delete_workflow_approvals(workflow, workspace) == 0
            with pytest.raises(grpc.aio.AioRpcError) as error:
                await client.stub.DeleteWorkflowApprovals(
                    messages.DeleteWorkflowApprovalsRequest(
                        workflow_id="invalid",
                        workspace_id=str(workspace),
                    )
                )
            assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
            assert session.commit.await_count == 2
        finally:
            await client.close()
            await server.stop(0)
            db.close()

    asyncio.run(exercise())


def test_cleanup_rolls_back_database_failure(monkeypatch):
    async def exercise():
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.execute.side_effect = RuntimeError("database failure")
        monkeypatch.setattr(execution_server, "AsyncSessionLocal", lambda: session)
        with pytest.raises(RuntimeError, match="database failure"):
            await execution_server.ExecutionInternalService().DeleteWorkflowApprovals(
                messages.DeleteWorkflowApprovalsRequest(
                    workflow_id=str(uuid4()), workspace_id=str(uuid4())
                ),
                AsyncMock(),
            )
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()

    asyncio.run(exercise())
