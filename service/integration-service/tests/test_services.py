import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookUpdate
from app.services import webhook_service as service


WORKSPACE_ID = uuid4()
WORKFLOW_ID = uuid4()
VERSION_ID = uuid4()
WEBHOOK_ID = uuid4()


class Result:
    def __init__(self, scalar=None, values=None):
        self.scalar = scalar
        self.values = values or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class FakeSession:
    def __init__(self, results=(), fail_commit=None):
        self.results = iter(results)
        self.added = []
        self.deleted = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = fail_commit

    async def execute(self, _statement):
        return next(self.results)

    def add(self, value):
        self.added.append(value)
        if getattr(value, "id", None) is None:
            value.id = WEBHOOK_ID

    async def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise self.fail_commit

    async def refresh(self, _value):
        return None

    async def rollback(self):
        self.rollbacks += 1

    async def delete(self, value):
        self.deleted.append(value)


def create_data(authentication_type="none"):
    return WebhookCreate(
        workflow_id=WORKFLOW_ID,
        workflow_version_id=VERSION_ID,
        name="Orders",
        event_name="order.created",
        method="POST",
        authentication_type=authentication_type,
    )


def test_validate_workflow_version_closes_client(monkeypatch):
    calls = []

    class WorkflowClient:
        async def validate_workflow_version(self, **kwargs):
            calls.append(("validate", kwargs))
            return SimpleNamespace(valid=True, status="published", workflow_status="active")

        async def close(self):
            calls.append(("close",))

    monkeypatch.setattr(service, "WorkflowGrpcClient", WorkflowClient)
    asyncio.run(service.validate_workflow_version(WORKFLOW_ID, VERSION_ID, WORKSPACE_ID))
    assert calls == [
        ("validate", {"workflow_id": str(WORKFLOW_ID), "version_id": str(VERSION_ID), "workspace_id": str(WORKSPACE_ID)}),
        ("close",),
    ]


def test_validate_workflow_version_closes_client_after_error(monkeypatch):
    closed = []

    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            raise RuntimeError("upstream error")

        async def close(self):
            closed.append(True)

    monkeypatch.setattr(service, "WorkflowGrpcClient", WorkflowClient)
    with pytest.raises(RuntimeError, match="upstream error"):
        asyncio.run(service.validate_workflow_version(WORKFLOW_ID, VERSION_ID, WORKSPACE_ID))
    assert closed == [True]


def test_validate_workflow_version_rejects_unpublished_and_closes_client(monkeypatch):
    closed = []

    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            return SimpleNamespace(valid=True, status="draft", workflow_status="active")

        async def close(self):
            closed.append(True)

    monkeypatch.setattr(service, "WorkflowGrpcClient", WorkflowClient)
    with pytest.raises(service.UnpublishedWorkflowVersionError):
        asyncio.run(service.validate_workflow_version(WORKFLOW_ID, VERSION_ID, WORKSPACE_ID))
    assert closed == [True]


def test_validate_workflow_version_rejects_inactive_workflow(monkeypatch):
    class WorkflowClient:
        async def validate_workflow_version(self, **_kwargs):
            return SimpleNamespace(valid=True, status="published", workflow_status="inactive")

        async def close(self):
            return None

    monkeypatch.setattr(service, "WorkflowGrpcClient", WorkflowClient)
    with pytest.raises(service.InactiveWorkflowError):
        asyncio.run(service.validate_workflow_version(WORKFLOW_ID, VERSION_ID, WORKSPACE_ID))


def test_token_and_secret_generation_and_verification(monkeypatch):
    monkeypatch.setattr(service.secrets, "token_urlsafe", lambda _length: "random-value")
    assert service.generate_public_token() == "random-value"
    assert service.generate_webhook_secret() == "rly_whsec_random-value"

    class Hasher:
        def verify(self, secret, hashed):
            return (secret, hashed) == ("secret", "hash")

    monkeypatch.setattr(service, "password_hash", Hasher())
    assert service.verify_webhook_secret("secret", "hash") is True
    assert service.verify_webhook_secret("wrong", "hash") is False


def test_create_webhook_with_secret_and_without(monkeypatch):
    async def validate(**_kwargs):
        return "published", None

    monkeypatch.setattr(service, "validate_workflow_version", validate)
    monkeypatch.setattr(service, "generate_public_token", lambda: "public")
    monkeypatch.setattr(service, "generate_webhook_secret", lambda: "one-time-secret")

    class Hasher:
        def hash(self, secret):
            assert secret == "one-time-secret"
            return "hashed-secret"

    monkeypatch.setattr(service, "password_hash", Hasher())
    secured_session = FakeSession()
    secured, secret = asyncio.run(service.create_webhook(create_data("secret"), WORKSPACE_ID, secured_session))
    assert secured.workspace_id == WORKSPACE_ID
    assert secured.secret_hash == "hashed-secret"
    assert secured.public_token == "public"
    assert secret == "one-time-secret"
    assert secured_session.commits == 1

    open_session = FakeSession()
    open_webhook, no_secret = asyncio.run(service.create_webhook(create_data(), WORKSPACE_ID, open_session))
    assert open_webhook.secret_hash is None
    assert no_secret is None


def test_create_webhook_requires_published_version_before_persisting(monkeypatch):
    async def validate(**_kwargs):
        raise service.UnpublishedWorkflowVersionError("Webhook workflow version must be published")

    monkeypatch.setattr(service, "validate_workflow_version", validate)
    session = FakeSession()
    with pytest.raises(service.UnpublishedWorkflowVersionError):
        asyncio.run(service.create_webhook(create_data(), WORKSPACE_ID, session))
    assert session.added == []
    assert session.commits == 0


def test_create_webhook_rolls_back_integrity_error(monkeypatch):
    async def validate(**_kwargs):
        return "published", None

    monkeypatch.setattr(service, "validate_workflow_version", validate)
    failure = IntegrityError("insert", {}, RuntimeError("duplicate"))
    session = FakeSession(fail_commit=failure)
    with pytest.raises(IntegrityError):
        asyncio.run(service.create_webhook(create_data(), WORKSPACE_ID, session))
    assert session.rollbacks == 1


def test_list_and_find_webhooks():
    expected = SimpleNamespace(id=WEBHOOK_ID)
    session = FakeSession([Result(values=[expected]), Result(scalar=expected), Result(scalar=expected)])
    assert asyncio.run(service.list_webhooks(WORKSPACE_ID, session)) == [expected]
    assert asyncio.run(service.get_webhook(WEBHOOK_ID, WORKSPACE_ID, session)) is expected
    assert asyncio.run(service.get_webhook_by_public_token("token", session)) is expected


def test_update_webhook_updates_only_set_fields_and_returns_missing():
    current = SimpleNamespace(name="Before", is_active=True)
    session = FakeSession([Result(scalar=current)])
    updated = asyncio.run(service.update_webhook(WEBHOOK_ID, WebhookUpdate(name="After"), WORKSPACE_ID, session))
    assert updated.name == "After"
    assert updated.is_active is True
    assert session.commits == 1
    assert asyncio.run(service.update_webhook(WEBHOOK_ID, WebhookUpdate(), WORKSPACE_ID, FakeSession([Result()]))) is None


def test_update_webhook_integrity_error_rolls_back():
    failure = IntegrityError("update", {}, RuntimeError("conflict"))
    session = FakeSession([Result(scalar=SimpleNamespace(name="Before"))], fail_commit=failure)
    with pytest.raises(IntegrityError):
        asyncio.run(service.update_webhook(WEBHOOK_ID, WebhookUpdate(name="After"), WORKSPACE_ID, session))
    assert session.rollbacks == 1


def test_update_webhook_rejects_unpublished_version_without_mutating(monkeypatch):
    current = SimpleNamespace(
        workflow_id=WORKFLOW_ID,
        workflow_version_id=VERSION_ID,
        name="Before",
        is_active=True,
    )
    calls = []

    async def validate(**kwargs):
        calls.append(kwargs)
        raise service.UnpublishedWorkflowVersionError("Webhook workflow version must be published")

    monkeypatch.setattr(service, "validate_workflow_version", validate)
    session = FakeSession([Result(scalar=current)])
    with pytest.raises(service.UnpublishedWorkflowVersionError):
        asyncio.run(service.update_webhook(
            WEBHOOK_ID,
            WebhookUpdate(workflow_version_id=uuid4()),
            WORKSPACE_ID,
            session,
        ))
    assert current.workflow_version_id == VERSION_ID
    assert session.commits == 0
    assert calls[0]["workflow_id"] == WORKFLOW_ID
    assert calls[0]["workspace_id"] == WORKSPACE_ID


def test_delete_webhook_and_rollback_on_failure():
    item = SimpleNamespace(id=WEBHOOK_ID)
    session = FakeSession([Result(scalar=item)])
    assert asyncio.run(service.delete_webhook(WEBHOOK_ID, WORKSPACE_ID, session)) is True
    assert session.deleted == [item]
    assert asyncio.run(service.delete_webhook(WEBHOOK_ID, WORKSPACE_ID, FakeSession([Result()]))) is False

    session = FakeSession([Result(scalar=item)], fail_commit=RuntimeError("db failure"))
    with pytest.raises(RuntimeError, match="db failure"):
        asyncio.run(service.delete_webhook(WEBHOOK_ID, WORKSPACE_ID, session))
    assert session.rollbacks == 1


def test_regenerate_webhook_token_and_integrity_error(monkeypatch):
    current = SimpleNamespace(public_token="old")
    monkeypatch.setattr(service, "generate_public_token", lambda: "new")
    session = FakeSession([Result(scalar=current)])
    assert asyncio.run(service.regenerate_webhook_token(WEBHOOK_ID, WORKSPACE_ID, session)) is current
    assert current.public_token == "new"
    assert asyncio.run(service.regenerate_webhook_token(WEBHOOK_ID, WORKSPACE_ID, FakeSession([Result()]))) is None

    failure = IntegrityError("update", {}, RuntimeError("duplicate"))
    session = FakeSession([Result(scalar=SimpleNamespace(public_token="old"))], fail_commit=failure)
    with pytest.raises(IntegrityError):
        asyncio.run(service.regenerate_webhook_token(WEBHOOK_ID, WORKSPACE_ID, session))
    assert session.rollbacks == 1


def test_webhook_model_has_database_table():
    assert Webhook.__tablename__ == "webhooks"
