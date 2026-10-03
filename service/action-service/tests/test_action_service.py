import asyncio
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.grpc import action_server
from app.grpc.generated.action import action_pb2
from app.connectors import gmail, http, mock_payment, registry
from app.schemas.connection import ConnectionCreate, ConnectionUpdate
from app.services import connection_service
from app.dependencies import get_current_identity
from app.routes import connections as connection_routes
from app.routes import gmail_oauth
from app.main import app as action_app


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


def make_request(**overrides):
    values = {
        "workspace_id": str(uuid4()),
        "connection_id": str(uuid4()),
        "provider": "mock_payment",
        "action": "refund_payment",
        "config_json": '{"mode": "test"}',
        "input_data_json": '{"payment_id": "pay-123", "amount": 25}',
    }
    values.update(overrides)
    return action_pb2.ExecuteActionRequest(**values)


def test_execute_action_uses_connection_and_connector(monkeypatch):
    connection = SimpleNamespace(auth_type="oauth2", credential="refresh-token")
    get_connection = SimpleNamespace(
        call=None,
    )

    async def lookup(**kwargs):
        get_connection.call = kwargs
        return connection

    class Connector:
        async def execute(self, action, config, input_data):
            assert action == "refund_payment"
            assert config == {"mode": "test", "refresh_token": "refresh-token"}
            assert input_data == {"payment_id": "pay-123", "amount": 25}
            return {"success": True, "refund_id": "r-1"}

    monkeypatch.setattr(action_server, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(action_server, "get_connection", lookup)
    monkeypatch.setattr(action_server.connector_registry, "get", lambda provider: Connector())

    response = asyncio.run(action_server.ActionInternalService().ExecuteAction(make_request(), None))

    assert response.success is True
    assert json.loads(response.result_json) == {"success": True, "refund_id": "r-1"}
    assert get_connection.call["workspace_id"]
    assert get_connection.call["connection_id"]


def test_execute_action_with_non_oauth_connection_and_empty_json(monkeypatch):
    monkeypatch.setattr(action_server, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(
        action_server,
        "get_connection",
        AsyncMockConnectionLookup(SimpleNamespace(auth_type="none", credential="ignored")),
    )

    class Connector:
        async def execute(self, action, config, input_data):
            assert config == {}
            assert input_data == {}
            return {"accepted": action}

    monkeypatch.setattr(action_server.connector_registry, "get", lambda _provider: Connector())
    request = make_request(config_json="", input_data_json="", action="request")
    response = asyncio.run(action_server.ActionInternalService().ExecuteAction(request, None))

    assert response.success is True
    assert json.loads(response.result_json) == {"accepted": "request"}


class AsyncMockConnectionLookup:
    def __init__(self, connection):
        self.connection = connection

    async def __call__(self, **_kwargs):
        return self.connection


def test_execute_action_returns_not_found(monkeypatch):
    monkeypatch.setattr(action_server, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(action_server, "get_connection", AsyncMockConnectionLookup(None))

    response = asyncio.run(action_server.ActionInternalService().ExecuteAction(make_request(), None))

    assert response.success is False
    assert response.error == "Connection not found"


@pytest.mark.parametrize(
    ("overrides", "expected_error"),
    [
        ({"workspace_id": "not-a-uuid"}, "badly formed hexadecimal UUID string"),
        (
            {"config_json": "{"},
            "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
        ),
        (
            {"input_data_json": "{"},
            "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)",
        ),
    ],
)
def test_execute_action_rejects_invalid_request_values(monkeypatch, overrides, expected_error):
    monkeypatch.setattr(action_server, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(
        action_server,
        "get_connection",
        AsyncMockConnectionLookup(SimpleNamespace(auth_type="none", credential=None)),
    )
    response = asyncio.run(
        action_server.ActionInternalService().ExecuteAction(make_request(**overrides), None)
    )

    assert response.success is False
    assert response.error == expected_error


def test_execute_action_reports_connector_errors(monkeypatch):
    monkeypatch.setattr(action_server, "AsyncSessionLocal", FakeSession)
    monkeypatch.setattr(
        action_server,
        "get_connection",
        AsyncMockConnectionLookup(SimpleNamespace(auth_type="none", credential=None)),
    )

    def fail_lookup(_provider):
        raise ValueError("Connector not found: missing")

    monkeypatch.setattr(action_server.connector_registry, "get", fail_lookup)
    response = asyncio.run(
        action_server.ActionInternalService().ExecuteAction(make_request(provider="missing"), None)
    )
    assert response.error == "Connector not found: missing"

    class BrokenConnector:
        async def execute(self, **_kwargs):
            raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(action_server.connector_registry, "get", lambda _provider: BrokenConnector())
    response = asyncio.run(action_server.ActionInternalService().ExecuteAction(make_request(), None))
    assert response.success is False
    assert response.error == "Action execution failed: upstream unavailable"


def test_connector_registry_and_mock_payment():
    connector_registry = registry.ConnectorRegistry()
    payment = mock_payment.MockPaymentConnector()
    connector_registry.register("payment", payment)
    assert connector_registry.get("payment") is payment
    with pytest.raises(ValueError, match="Connector not found: missing"):
        connector_registry.get("missing")

    result = asyncio.run(payment.execute("refund_payment", {}, {"payment_id": "p1", "amount": 9}))
    assert result["success"] is True
    assert result["payment_id"] == "p1"
    assert result["amount"] == 9
    assert result["status"] == "refunded"
    assert result["refund_id"]
    with pytest.raises(ValueError, match="Unsupported payment action"):
        asyncio.run(payment.execute("capture", {}, {}))
    with pytest.raises(ValueError, match="Payment ID is required"):
        asyncio.run(payment.execute("refund_payment", {}, {"amount": 9}))
    with pytest.raises(ValueError, match="Refund amount is required"):
        asyncio.run(payment.execute("refund_payment", {}, {"payment_id": "p1"}))


def test_http_connector_success_text_and_validation(monkeypatch):
    calls = []

    class Response:
        status_code = 201
        headers = {"content-type": "text/plain"}
        is_success = True
        text = "created"

        def json(self):
            raise ValueError("not json")

    class Client:
        def __init__(self, **kwargs):
            calls.append(("client", kwargs))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def request(self, **kwargs):
            calls.append(("request", kwargs))
            return Response()

    monkeypatch.setattr(http.httpx, "AsyncClient", Client)
    connector = http.HTTPConnector()
    result = asyncio.run(connector.execute(
        "request", {"timeout": 3},
        {"method": "post", "url": "https://example.test", "headers": {"x": "y"}, "params": {"q": 1}, "body": {"ok": True}},
    ))
    assert result == {"status_code": 201, "headers": {"content-type": "text/plain"}, "body": "created", "success": True}
    assert calls[0] == ("client", {"timeout": 3})
    assert calls[1][1] == {"method": "POST", "url": "https://example.test", "headers": {"x": "y"}, "params": {"q": 1}, "json": {"ok": True}}

    with pytest.raises(ValueError, match="Unsupported HTTP action"):
        asyncio.run(connector.execute("delete", {}, {}))
    with pytest.raises(ValueError, match="HTTP request URL is required"):
        asyncio.run(connector.execute("request", {}, {}))


def test_gmail_connector_and_token_refresh(monkeypatch):
    with pytest.raises(ValueError, match="Unsupported Gmail action"):
        asyncio.run(gmail.GmailConnector().execute("read", {}, {}))
    with pytest.raises(ValueError, match="Gmail refresh token is required"):
        asyncio.run(gmail.GmailConnector().execute("send_email", {}, {}))
    for input_data, message in [
        ({"subject": "s", "body": "b"}, "Recipient email is required"),
        ({"to": "a@example.test", "body": "b"}, "Email subject is required"),
        ({"to": "a@example.test", "subject": "s"}, "Email body is required"),
    ]:
        with pytest.raises(ValueError, match=message):
            asyncio.run(gmail.GmailConnector().execute("send_email", {"refresh_token": "r"}, input_data))

    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        asyncio.run(gmail.refresh_access_token("refresh"))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")

    class TokenResponse:
        status_code = 200
        def json(self):
            return {"access_token": "access"}

    class GmailResponse:
        status_code = 202
        def json(self):
            return {"id": "message", "threadId": "thread", "labelIds": ["SENT"]}

    class Client:
        def __init__(self, **_kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_args):
            return False
        async def post(self, url, **_kwargs):
            if "oauth2" in url:
                return TokenResponse()
            return GmailResponse()

    monkeypatch.setattr(gmail.httpx, "AsyncClient", Client)
    result = asyncio.run(gmail.GmailConnector().execute(
        "send_email", {"refresh_token": "refresh"},
        {"to": "a@example.test", "subject": "hello", "body": "world"},
    ))
    assert result == {"success": True, "message_id": "message", "thread_id": "thread", "label_ids": ["SENT"]}
    assert base64.urlsafe_b64encode(b"test")


def test_connection_service_crud_and_validation(monkeypatch):
    workspace_id = uuid4()
    connection_id = uuid4()

    class Session(FakeSession):
        def __init__(self, result=None):
            self.result = result
            self.calls = []
        async def execute(self, statement):
            self.calls.append(statement)
            return self.result
        def add(self, item): self.calls.append(("add", item))
        async def commit(self): self.calls.append(("commit",))
        async def refresh(self, item): self.calls.append(("refresh", item))
        async def rollback(self): self.calls.append(("rollback",))

    class Result:
        def __init__(self, row=None, rows=(), rowcount=1):
            self.row = row
            self.rows = rows
            self.rowcount = rowcount
        def scalar_one_or_none(self): return self.row
        def scalars(self): return SimpleNamespace(all=lambda: list(self.rows))

    created = SimpleNamespace()
    session = Session()
    monkeypatch.setattr(connection_service, "Connection", action_server.get_connection.__globals__["Connection"])
    async def fake_commit(): session.calls.append(("commit",))
    session.commit = fake_commit
    async def fake_refresh(item):
        created.object = item
    session.refresh = fake_refresh
    result = asyncio.run(connection_service.create_connection(
        ConnectionCreate(name="API", provider="http", auth_type="none"), workspace_id, session
    ))
    assert result is created.object
    assert result.workspace_id == workspace_id

    row = SimpleNamespace(id=connection_id)
    session = Session(Result(row, [row]))
    assert asyncio.run(connection_service.get_connections(workspace_id, session)) == [row]
    assert asyncio.run(connection_service.get_connection(connection_id, workspace_id, session)) is row

    session = Session(Result(row))
    assert asyncio.run(connection_service.update_connection(
        connection_id, workspace_id, ConnectionUpdate(name="Updated"), session
    )) is row
    assert session.calls[-1] == ("commit",)
    session = Session(Result())
    assert asyncio.run(connection_service.update_connection(
        connection_id, workspace_id, ConnectionUpdate(), session
    )) is None
    assert asyncio.run(connection_service.update_connection(
        connection_id, workspace_id, ConnectionUpdate(name="Updated"), session
    )) is None
    assert session.calls[-1] == ("rollback",)

    session = Session(Result(rowcount=0))
    assert asyncio.run(connection_service.delete_connection(connection_id, workspace_id, session)) is False
    assert session.calls[-1] == ("rollback",)
    session = Session(Result(rowcount=1))
    assert asyncio.run(connection_service.delete_connection(connection_id, workspace_id, session)) is True
    assert session.calls[-1] == ("commit",)


def test_connection_test_auth_paths_and_http_responses(monkeypatch):
    connection = SimpleNamespace(provider="http", config={"test_url": "https://example.test"}, auth_type="none", credential=None)
    session = FakeSession()
    async def lookup(**_kwargs): return connection
    monkeypatch.setattr(connection_service, "get_connection", lookup)
    with pytest.raises(ValueError, match="Connection not found"):
        async def missing(**_kwargs): return None
        monkeypatch.setattr(connection_service, "get_connection", missing)
        asyncio.run(connection_service.test_connection(uuid4(), uuid4(), session))
    monkeypatch.setattr(connection_service, "get_connection", lookup)

    async def check_error(auth_type, credential, config, expected):
        connection.auth_type, connection.credential, connection.config = auth_type, credential, config
        with pytest.raises(ValueError, match=expected):
            await connection_service.test_connection(uuid4(), uuid4(), session)
    async def run_validation():
        connection.provider = "gmail"
        await check_error("none", None, {}, "Unsupported connection provider")
        connection.provider = "http"
        await check_error("none", None, {}, "config.test_url is required")
        await check_error("bearer", None, {"test_url": "url"}, "Credential is required")
        await check_error("api_key_header", None, {"test_url": "url"}, "Credential is required")
        await check_error("api_key_header", "key", {"test_url": "url"}, "config.auth_header is required")
        await check_error("api_key_query", None, {"test_url": "url"}, "Credential is required")
        await check_error("api_key_query", "key", {"test_url": "url"}, "config.auth_param is required")
        await check_error("other", "key", {"test_url": "url"}, "Unsupported auth_type")
    asyncio.run(run_validation())

    class Response:
        def __init__(self, status, payload): self.status_code, self.payload = status, payload
        def json(self):
            if isinstance(self.payload, ValueError): raise self.payload
            return self.payload
        @property
        def text(self): return "plain"
    class Client:
        response = Response(200, {"ok": True})
        def __init__(self, **kwargs): self.kwargs = kwargs
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return False
        async def get(self, _url, **kwargs): self.request = kwargs; return self.response
    monkeypatch.setattr(connection_service.httpx, "AsyncClient", Client)
    async def test_auth(auth_type, credential, config):
        connection.auth_type, connection.credential, connection.config = auth_type, credential, config
        return await connection_service.test_connection(uuid4(), uuid4(), session)
    result = asyncio.run(test_auth("bearer", "secret", {"test_url": "url"}))
    assert result.success and result.response == {"ok": True}
    result = asyncio.run(test_auth("api_key_header", "secret", {"test_url": "url", "auth_header": "X-Key"}))
    assert result.success
    result = asyncio.run(test_auth("api_key_query", "secret", {"test_url": "url", "auth_param": "key"}))
    assert result.success
    Client.response = Response(500, ValueError("not json"))
    result = asyncio.run(test_auth("none", None, {"test_url": "url"}))
    assert not result.success and result.status_code == 500 and result.response == "plain"


def test_connection_create_schema_validation():
    assert ConnectionCreate(name="x", provider="http", auth_type="none").credential is None
    assert ConnectionCreate(name="x", provider="gmail", auth_type="oauth2", credential="secret")
    with pytest.raises(ValueError, match="Unsupported auth_type"):
        ConnectionCreate(name="x", provider="http", auth_type="invalid")
    with pytest.raises(ValueError, match="credential is required"):
        ConnectionCreate(name="x", provider="http", auth_type="bearer")
    with pytest.raises(ValueError, match="config.auth_header is required"):
        ConnectionCreate(name="x", provider="http", auth_type="api_key_header", credential="secret")
    with pytest.raises(ValueError, match="config.auth_param is required"):
        ConnectionCreate(name="x", provider="http", auth_type="api_key_query", credential="secret")


def test_identity_authentication_paths(monkeypatch):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as no_auth:
        asyncio.run(get_current_identity(authorization=None, access_cookie=None))
    assert no_auth.value.status_code == 401
    with pytest.raises(HTTPException) as bad_scheme:
        asyncio.run(get_current_identity(authorization="Basic abc", access_cookie=None))
    assert bad_scheme.value.status_code == 401

    class Client:
        async def validate_token(self, token):
            assert token == "cookie-token"
            return SimpleNamespace(valid=True, user_id="user", workspace_id="workspace")
        async def close(self): pass
    monkeypatch.setattr("app.dependencies.AuthGrpcClient", Client)
    assert asyncio.run(get_current_identity(authorization=None, access_cookie="cookie-token")) == {
        "user_id": "user", "workspace_id": "workspace"
    }

    class InvalidClient(Client):
        async def validate_token(self, _token): return SimpleNamespace(valid=False)
    monkeypatch.setattr("app.dependencies.AuthGrpcClient", InvalidClient)
    with pytest.raises(HTTPException) as invalid:
        asyncio.run(get_current_identity(authorization="Bearer bad", access_cookie=None))
    assert invalid.value.status_code == 401

    class DownClient(Client):
        async def validate_token(self, _token): raise RuntimeError("down")
    monkeypatch.setattr("app.dependencies.AuthGrpcClient", DownClient)
    with pytest.raises(HTTPException) as unavailable:
        asyncio.run(get_current_identity(authorization="Bearer token", access_cookie=None))
    assert unavailable.value.status_code == 503


def test_connection_routes_success_and_error_paths(monkeypatch):
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError

    workspace_id = str(uuid4())
    connection_id = uuid4()
    identity = {"workspace_id": workspace_id}
    session = FakeSession()
    data = ConnectionCreate(name="API", provider="http", auth_type="none")
    row = SimpleNamespace(id=connection_id)

    async def return_row(**_kwargs): return row
    async def return_rows(**_kwargs): return [row]
    async def return_true(**_kwargs): return True
    async def return_test(**_kwargs): return SimpleNamespace(success=True)
    monkeypatch.setattr(connection_routes, "create_connection", return_row)
    monkeypatch.setattr(connection_routes, "get_connections", return_rows)
    monkeypatch.setattr(connection_routes, "get_connection", return_row)
    monkeypatch.setattr(connection_routes, "update_connection", return_row)
    monkeypatch.setattr(connection_routes, "delete_connection", return_true)
    monkeypatch.setattr(connection_routes, "test_connection", return_test)

    async def run_success():
        assert await connection_routes.create_connection_route(data, identity, session) is row
        assert await connection_routes.get_connections_route(identity, session) == [row]
        assert await connection_routes.get_connection_route(connection_id, identity, session) is row
        assert await connection_routes.update_connection_route(connection_id, ConnectionUpdate(name="New"), identity, session) is row
        assert await connection_routes.delete_connection_route(connection_id, identity, session) is None
        assert (await connection_routes.test_connection_route(connection_id, identity, session)).success
    asyncio.run(run_success())

    async def expect_http(call, status, detail=None):
        with pytest.raises(HTTPException) as error:
            await call
        assert error.value.status_code == status
        if detail is not None: assert error.value.detail == detail
    bad_identity = {"workspace_id": "bad"}
    async def bad_identity_cases():
        await expect_http(connection_routes.create_connection_route(data, bad_identity, session), 401)
        await expect_http(connection_routes.get_connections_route(bad_identity, session), 401)
        await expect_http(connection_routes.get_connection_route(connection_id, bad_identity, session), 401)
        await expect_http(connection_routes.update_connection_route(connection_id, ConnectionUpdate(name="N"), bad_identity, session), 401)
        await expect_http(connection_routes.delete_connection_route(connection_id, bad_identity, session), 401)
        await expect_http(connection_routes.test_connection_route(connection_id, bad_identity, session), 401)
    asyncio.run(bad_identity_cases())

    async def missing(**_kwargs): return None
    async def deleted(**_kwargs): return False
    async def value_error(**_kwargs): raise ValueError("Unsupported auth_type: none")
    async def sql_error(**_kwargs): raise SQLAlchemyError("db")
    monkeypatch.setattr(connection_routes, "get_connection", missing)
    monkeypatch.setattr(connection_routes, "update_connection", missing)
    monkeypatch.setattr(connection_routes, "delete_connection", deleted)
    async def missing_cases():
        await expect_http(connection_routes.get_connection_route(connection_id, identity, session), 404)
        await expect_http(connection_routes.update_connection_route(connection_id, ConnectionUpdate(name="N"), identity, session), 404)
        await expect_http(connection_routes.delete_connection_route(connection_id, identity, session), 404)
    asyncio.run(missing_cases())
    monkeypatch.setattr(connection_routes, "test_connection", value_error)
    asyncio.run(expect_http(connection_routes.test_connection_route(connection_id, identity, session), 400))
    async def conn_missing(**_kwargs): raise ValueError("Connection not found")
    monkeypatch.setattr(connection_routes, "test_connection", conn_missing)
    asyncio.run(expect_http(connection_routes.test_connection_route(connection_id, identity, session), 404))
    for name in ("create_connection", "get_connections", "get_connection", "update_connection", "delete_connection", "test_connection"):
        monkeypatch.setattr(connection_routes, name, sql_error)
    async def sql_cases():
        for call in (
            connection_routes.create_connection_route(data, identity, session),
            connection_routes.get_connections_route(identity, session),
            connection_routes.get_connection_route(connection_id, identity, session),
            connection_routes.update_connection_route(connection_id, ConnectionUpdate(name="N"), identity, session),
            connection_routes.delete_connection_route(connection_id, identity, session),
            connection_routes.test_connection_route(connection_id, identity, session),
        ):
            await expect_http(call, 500)
    asyncio.run(sql_cases())
    assert action_app is not None


def test_gmail_oauth_exchange_helpers(monkeypatch):
    for name in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_GMAIL_REDIRECT_URI"):
        monkeypatch.delenv(name, raising=False)
    class NoopClient:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return False
        async def post(self, *_args, **_kwargs): raise AssertionError("HTTP call should not be reached")
    monkeypatch.setattr(gmail_oauth.httpx, "AsyncClient", NoopClient)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        asyncio.run(gmail_oauth.exchange_google_code("code"))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_SECRET"):
        asyncio.run(gmail_oauth.exchange_google_code("code"))
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    with pytest.raises(RuntimeError, match="GOOGLE_GMAIL_REDIRECT_URI"):
        asyncio.run(gmail_oauth.exchange_google_code("code"))
    monkeypatch.setenv("GOOGLE_GMAIL_REDIRECT_URI", "https://app.test/callback")

    class Response:
        def __init__(self, payload, status_code=200):
            self.status_code = status_code
            self.payload = payload
        @property
        def text(self): return "failure"
        def json(self): return self.payload

    class Client:
        response = None
        def __init__(self, **_kwargs): self.response = Client.response
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return False
        async def post(self, *_args, **_kwargs): return self.response
        async def get(self, *_args, **_kwargs): return self.response

    monkeypatch.setattr(gmail_oauth.httpx, "AsyncClient", Client)
    Client.response = Response({"access_token": "token"})
    assert asyncio.run(gmail_oauth.exchange_google_code("code")) == {"access_token": "token"}
    Client.response = Response({"email": "user@example.test"})
    assert asyncio.run(gmail_oauth.get_google_user_email("token")) == "user@example.test"
    Client.response = Response({})
    with pytest.raises(RuntimeError, match="email was not returned"):
        asyncio.run(gmail_oauth.get_google_user_email("token"))

    Client.response = Response({}, status_code=400)
    with pytest.raises(RuntimeError, match="token exchange failed"):
        asyncio.run(gmail_oauth.exchange_google_code("code"))


def test_gmail_oauth_routes_state_and_callback(monkeypatch):
    from fastapi import HTTPException

    class FakeOAuthState:
        state = None
        provider = None
        def __init__(self, **kwargs): self.__dict__.update(kwargs)
    class FakeConnection:
        _id = 0
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.id = uuid4()
    monkeypatch.setattr(gmail_oauth, "OAuthState", FakeOAuthState)
    monkeypatch.setattr(gmail_oauth, "select", lambda _model: SimpleNamespace(where=lambda *_args: "statement"))
    monkeypatch.setattr(gmail_oauth, "Connection", FakeConnection)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_GMAIL_REDIRECT_URI", "https://app.test/callback")
    class Session(FakeSession):
        def __init__(self, result=None): self.result = result; self.calls = []
        def add(self, item): self.calls.append(("add", item))
        async def commit(self): self.calls.append(("commit",))
        async def execute(self, _statement): return self.result
        async def delete(self, item): self.calls.append(("delete", item))
        async def refresh(self, item): self.calls.append(("refresh", item))
    session = Session()
    monkeypatch.setattr(gmail_oauth, "AsyncSessionLocal", lambda: session)
    redirect = asyncio.run(gmail_oauth.start_gmail_oauth({"workspace_id": str(uuid4())}))
    assert redirect.status_code == 302 and "accounts.google.com" in redirect.headers["location"]
    assert any(call[0] == "commit" for call in session.calls)

    async def expect_callback_error(code, state, error, message):
        with pytest.raises(HTTPException) as raised:
            await gmail_oauth.gmail_oauth_callback(
                code=code, state=state, error=error or None
            )
        assert raised.value.status_code == 400 and message in raised.value.detail
    asyncio.run(expect_callback_error(None, None, "access_denied", "authorization failed"))
    asyncio.run(expect_callback_error(None, "s", None, "code is missing"))
    asyncio.run(expect_callback_error("c", None, None, "state is missing"))
    session.result = SimpleNamespace(scalar_one_or_none=lambda: None)
    asyncio.run(expect_callback_error("c", "bad", None, "Invalid OAuth state"))
    expired = FakeOAuthState(state="expired", workspace_id=uuid4(), expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    session.result = SimpleNamespace(scalar_one_or_none=lambda: expired)
    asyncio.run(expect_callback_error("c", "expired", None, "expired"))

    valid = FakeOAuthState(state="ok", workspace_id=uuid4(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=1))
    session.result = SimpleNamespace(scalar_one_or_none=lambda: valid)
    async def tokens(_code): return {"access_token": "access"}
    monkeypatch.setattr(gmail_oauth, "exchange_google_code", tokens)
    asyncio.run(expect_callback_error("c", "ok", None, "refresh token was not returned"))
    async def tokens(_code): return {"access_token": "access", "refresh_token": "refresh"}
    monkeypatch.setattr(gmail_oauth, "exchange_google_code", tokens)
    async def email(_token): return "user@example.test"
    monkeypatch.setattr(gmail_oauth, "get_google_user_email", email)
    result = asyncio.run(gmail_oauth.gmail_oauth_callback(code="c", state="ok", error=None))
    assert result["message"] == "Gmail connected successfully"
    assert result["email"] == "user@example.test"
    assert any(call[0] == "delete" for call in session.calls)
