from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
import grpc
import pytest
from app.services import webhook_lifecycle as lifecycle

@pytest.mark.parametrize('activate', [False, True])
@pytest.mark.parametrize('fails', [False, True])
async def test_webhook_lifecycle_closes_client(monkeypatch, activate, fails):
    call = AsyncMock(return_value=3)
    if fails:
        call.side_effect = grpc.aio.AioRpcError(grpc.StatusCode.UNAVAILABLE, (), (), 'offline')
    client = SimpleNamespace(delete_workflow_webhooks=call, activate_workflow_version_webhooks=call, close=AsyncMock())
    monkeypatch.setattr(lifecycle,'IntegrationGrpcClient',lambda:client)
    function = lifecycle.activate_workflow_version_webhooks if activate else lifecycle.revoke_workflow_webhooks
    ids = [uuid4() for _ in range(3)]
    if fails:
        with pytest.raises(lifecycle.WebhookActivationError if activate else lifecycle.WebhookCleanupError):
            await function(*ids)
    else:
        result = await function(*ids)
        assert result == (3 if activate else None)
    client.close.assert_awaited_once()
    call.assert_awaited_once_with(workflow_id=ids[0], workspace_id=ids[1], workflow_version_id=ids[2])

@pytest.mark.parametrize('operation', ['delete_workflow_webhooks', 'activate_workflow_version_webhooks', 'sync_workflow_schedule', 'suspend_workflow_schedule', 'delete_workflow_schedule'])
async def test_integration_transport_and_identifiers(monkeypatch, operation):
    from app.grpc import integration_client as transport
    channel = SimpleNamespace(close=AsyncMock())
    call = AsyncMock(return_value=SimpleNamespace(deleted_count=2, activated_count=2, affected_count=2))
    stub = SimpleNamespace(**{name: call for name in ['DeleteWorkflowWebhooks','ActivateWorkflowVersionWebhooks','SyncWorkflowSchedule','SuspendWorkflowSchedule','DeleteWorkflowSchedule']})
    monkeypatch.setattr(transport.grpc.aio, 'insecure_channel', lambda _:channel)
    monkeypatch.setattr(transport.webhook_lifecycle_pb2_grpc,'IntegrationInternalServiceStub',lambda _:stub)
    client = transport.IntegrationGrpcClient()
    workflow_id,workspace_id,version_id = [uuid4() for _ in range(3)]
    kwargs = dict(workflow_id=workflow_id,workspace_id=workspace_id)
    if operation in {'delete_workflow_webhooks','activate_workflow_version_webhooks','sync_workflow_schedule'}:
        kwargs['workflow_version_id'] = version_id
    if operation == 'sync_workflow_schedule':
        kwargs.update(has_schedule_trigger=True,workflow_active=True)
    assert await getattr(client,operation)(**kwargs) == 2
    request = call.await_args.args[0]
    assert request.workspace_id == str(workspace_id) and request.workflow_id == str(workflow_id)
    assert call.await_args.kwargs == {'timeout':8.0}
    await client.close()
    channel.close.assert_awaited_once()
