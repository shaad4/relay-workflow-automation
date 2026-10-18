import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.workflow import WorkflowResponse
from app.services import workflow_service as service
from test_workflow_service import FakeSession, Result


def test_workflow_response_exposes_actual_published_pointer():
    version_id = uuid4()
    workflow = NS(id=uuid4(), workspace_id=uuid4(), name="Scheduled", description=None,
                  status="active", published_version_id=version_id,
                  created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    assert WorkflowResponse.model_validate(workflow).published_version_id == version_id
    del workflow.published_version_id
    assert WorkflowResponse.model_validate(workflow).published_version_id is None


def test_post_commit_schedule_error_preserves_publication(monkeypatch):
    workflow_id, workspace_id, version_id = uuid4(), uuid4(), uuid4()
    workflow = NS(id=workflow_id, status="inactive", published_version_id=None)
    version = NS(id=version_id, version=2, status="draft")
    session = FakeSession([Result(scalar=workflow), Result(scalar=version)])
    closed = []

    async def validate(**kwargs): return {"valid": True}
    async def has_trigger(*args): return True

    class Client:
        async def sync_workflow_schedule(self, **kwargs):
            assert session.commits == 1
            raise RuntimeError("RPC unavailable")
        async def close(self): closed.append(True)

    monkeypatch.setattr(service, "validate_workflow", validate)
    monkeypatch.setattr(service, "_published_version_has_schedule_trigger", has_trigger)
    monkeypatch.setattr(service, "IntegrationGrpcClient", Client)
    with pytest.raises(service.ScheduleSynchronizationError, match="was published"):
        asyncio.run(service.publish_workflow(workflow_id, 2, workspace_id, session))
    assert workflow.published_version_id == version_id
    assert workflow.status == "active"
    assert version.status == "published"
    assert session.commits == 1
    assert session.rollbacks == 0
    assert closed == [True]
