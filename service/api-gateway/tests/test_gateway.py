import sys
import asyncio
import gzip
from types import SimpleNamespace
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import main
from app.core import proxy, security


ASGI_HTTPX_CLIENT = httpx.AsyncClient


class GatewayClient:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, **kwargs):
        async def send():
            async with ASGI_HTTPX_CLIENT(
                transport=httpx.ASGITransport(app=self.app),
                base_url="http://testserver",
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def options(self, path, **kwargs):
        return self.request("OPTIONS", path, **kwargs)


@pytest.fixture
def gateway_client():
    yield GatewayClient(main.app)


def fake_upstream(monkeypatch, *, status_code=200, headers=None, content=b'{"ok":true}'):
    calls = []

    class AsyncClient:
        def __init__(self, **kwargs):
            calls.append({"client_options": kwargs})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def request(self, **kwargs):
            calls.append(kwargs)
            return httpx.Response(status_code, content=content, headers=headers)

        async def get(self, url, **kwargs):
            calls.append({"method": "GET", "url": url, **kwargs})
            return httpx.Response(status_code, content=content, headers=headers)

    monkeypatch.setattr(httpx, "AsyncClient", AsyncClient)
    return calls


def access_token(monkeypatch):
    secret = "gateway-test-secret-that-is-at-least-32-bytes"
    monkeypatch.setattr(security, "JWT_SECRET_KEY", secret)
    return "auth-service-access-token"


def test_health_and_cors(gateway_client):
    response = gateway_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api-gateway"}

    cors = gateway_client.options(
        "/workflows/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert cors.status_code == 200
    assert "http://localhost:3000" in cors.headers["access-control-allow-origin"]



def test_gmail_oauth_start_preserves_google_redirect(gateway_client, monkeypatch):
    location = "https://accounts.google.com/o/oauth2/v2/auth?state=test"
    fake_upstream(
        monkeypatch,
        status_code=302,
        headers={"location": location},
        content=b"",
    )

    response = gateway_client.get("/connections/gmail/oauth/start", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == location


def test_gmail_oauth_callback_redirects_to_connections(gateway_client, monkeypatch):
    fake_upstream(
        monkeypatch,
        status_code=200,
        headers={"content-type": "application/json"},
        content=b'{"message":"Gmail connected successfully"}',
    )

    response = gateway_client.get(
        "/connections/gmail/oauth/callback?code=auth-code&state=oauth-state",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:3000/connections?gmail=connected"


def test_gmail_oauth_callback_reports_failure(gateway_client, monkeypatch):
    fake_upstream(
        monkeypatch,
        status_code=400,
        headers={"content-type": "application/json"},
        content=b'{"detail":"authorization failed"}',
    )

    response = gateway_client.get(
        "/connections/gmail/oauth/callback?error=access_denied",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:3000/connections?gmail=error"

def test_auth_me_validates_token_and_calls_auth_service(gateway_client, monkeypatch):
    token = access_token(monkeypatch)
    monkeypatch.setattr(
        "app.dependencies.verify_access_token",
        lambda received: {
            "sub": "user-1",
            "workspace_id": "workspace-1",
            "type": "access",
        } if received == token else (_ for _ in ()).throw(ValueError("invalid token")),
    )
    calls = fake_upstream(
        monkeypatch,
        status_code=200,
        headers={"content-type": "application/json", "x-auth-service": "auth"},
    )
    response = gateway_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls[-1]["url"].endswith("/auth/me")
    assert calls[-1]["headers"]["Authorization"] == f"Bearer {token}"
    assert response.headers["x-auth-service"] == "auth"


def test_auth_me_accepts_access_cookie_and_forwards_bearer(gateway_client, monkeypatch):
    token = access_token(monkeypatch)
    monkeypatch.setattr(
        "app.dependencies.verify_access_token",
        lambda received: {"sub": "user-1", "workspace_id": "workspace-1", "type": "access"}
        if received == token else (_ for _ in ()).throw(ValueError("invalid token")),
    )
    calls = fake_upstream(monkeypatch)

    response = gateway_client.get(
        "/auth/me",
        headers={"Cookie": f"relay_access_token={token}"},
    )

    assert response.status_code == 200
    assert calls[-1]["headers"]["Authorization"] == f"Bearer {token}"


def test_cookie_auth_allows_postman_without_origin(gateway_client, monkeypatch):
    calls = fake_upstream(monkeypatch)

    response = gateway_client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "secret"},
        headers={"Cookie": "relay_refresh_token=stored-refresh"},
    )

    assert response.status_code == 200
    assert len(calls) == 2


def test_cookie_auth_rejects_untrusted_origin(gateway_client, monkeypatch):
    calls = fake_upstream(monkeypatch)

    response = gateway_client.post(
        "/auth/refresh",
        headers={
            "Cookie": "relay_refresh_token=stored-refresh",
            "Origin": "https://attacker.example",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Untrusted request origin"
    assert len(calls) == 0


def test_cookie_auth_rejects_cross_site_fetch_without_origin(gateway_client, monkeypatch):
    calls = fake_upstream(monkeypatch)

    response = gateway_client.post(
        "/auth/refresh",
        headers={
            "Cookie": "relay_refresh_token=stored-refresh",
            "Sec-Fetch-Site": "cross-site",
        },
    )

    assert response.status_code == 403
    assert len(calls) == 0


def test_gateway_to_auth_service_me_integration(monkeypatch):
    from fastapi import FastAPI, Header
    from app import dependencies

    token = access_token(monkeypatch)
    monkeypatch.setattr(
        dependencies,
        "verify_access_token",
        lambda received: {
            "sub": "user-1",
            "workspace_id": "workspace-1",
            "type": "access",
        } if received == token else (_ for _ in ()).throw(ValueError("invalid token")),
    )
    auth_app = FastAPI()

    @auth_app.get("/auth/me")
    async def auth_service_current_user(authorization: str = Header()):
        assert authorization == f"Bearer {token}"
        return {
            "id": "user-1",
            "workspace_id": "workspace-1",
            "name": "Integrated User",
            "email": "integrated@example.com",
        }

    class AuthServiceHTTPClient:
        def __init__(self, **kwargs):
            self.client = ASGI_HTTPX_CLIENT(
                transport=httpx.ASGITransport(app=auth_app),
                base_url="http://auth-service:8000",
                **kwargs,
            )

        async def __aenter__(self):
            await self.client.__aenter__()
            return self

        async def __aexit__(self, *args):
            return await self.client.__aexit__(*args)

        async def get(self, url, **kwargs):
            return await self.client.get(url, **kwargs)

        async def request(self, *args, **kwargs):
            return await self.client.request(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", AuthServiceHTTPClient)
    client = GatewayClient(main.app)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["name"] == "Integrated User"
    assert response.json()["email"] == "integrated@example.com"


@pytest.mark.parametrize(
    ("authorization", "expected_detail"),
    [
        (None, "Authorization header is required"),
        ("Basic token", "Invalid authorization header"),
        ("Bearer ", "Invalid authorization header"),
        ("Bearer bad-token", "Invalid or expired access token"),
    ],
)
def test_auth_me_rejects_invalid_authorization(gateway_client, monkeypatch, authorization, expected_detail):
    fake_upstream(monkeypatch)
    headers = {} if authorization is None else {"Authorization": authorization}
    response = gateway_client.get("/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == expected_detail


def test_security_requires_access_token_and_identity(monkeypatch):
    from app.core.security import verify_access_token

    token = access_token(monkeypatch)
    monkeypatch.setattr(
        security,
        "jwt",
        SimpleNamespace(decode=lambda value, *_args, **_kwargs: {
            "sub": "user-1", "workspace_id": "workspace-1", "type": "access"
        }),
    )
    assert verify_access_token(token)["sub"] == "user-1"

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        monkeypatch.setattr(security, "JWT_SECRET_KEY", None)
        verify_access_token(token)

    monkeypatch.setattr(security, "JWT_SECRET_KEY", "gateway-test-secret-that-is-at-least-32-bytes")
    for payload in (
        {"sub": "user", "workspace_id": "workspace", "type": "refresh"},
        {"workspace_id": "workspace", "type": "access"},
        {"sub": "user", "type": "access"},
    ):
        monkeypatch.setattr(
            security,
            "jwt",
            SimpleNamespace(decode=lambda *_args, **_kwargs: payload),
        )
        with pytest.raises(ValueError):
            verify_access_token("signed-token")


@pytest.mark.parametrize(
    ("method", "path", "expected_path"),
    [
        ("POST", "/auth/login", "/auth/login"),
        ("POST", "/auth/register", "/auth/register"),
        ("POST", "/auth/refresh", "/auth/refresh"),
        ("POST", "/auth/forgot-password", "/auth/forgot-password"),
        ("POST", "/auth/reset-password", "/auth/reset-password"),
        ("GET", "/auth/verify-email?token=t", "/auth/verify-email"),
        ("POST", "/auth/resend-verification", "/auth/resend-verification"),
        ("GET", "/auth/google", "/auth/google"),
        ("GET", "/auth/google/callback?state=s&code=c", "/auth/google/callback"),
        ("POST", "/auth/google/complete", "/auth/google/complete"),
        ("POST", "/auth/google/exchange", "/auth/google/exchange"),
    ],
)
def test_public_auth_routes_proxy_to_auth_service(
    gateway_client, monkeypatch, method, path, expected_path
):
    calls = fake_upstream(monkeypatch, status_code=202, headers={"x-upstream": "auth"})
    response = gateway_client.request(method, path, json={"payload": "value"} if method == "POST" else None)
    assert response.status_code == 202
    assert response.headers["x-upstream"] == "auth"
    forwarded = calls[-1]
    parsed = urlparse(forwarded["url"])
    assert parsed.path.endswith(expected_path)
    if path in {"/auth/google", "/auth/google/callback?state=s&code=c"}:
        assert calls[0]["client_options"].get("follow_redirects") is False


@pytest.mark.parametrize(
    ("method", "path", "expected_path"),
    [
        ("GET", "/workflows/", "/workflows/"),
        ("POST", "/workflows/", "/workflows/"),
        ("GET", "/workflows/wf-1/", "/workflows/wf-1/"),
        ("PATCH", "/workflows/wf-1/", "/workflows/wf-1/"),
        ("DELETE", "/workflows/wf-1/", "/workflows/wf-1/"),
        ("GET", "/workflows/wf-1/versions/", "/workflows/wf-1/versions/"),
        ("GET", "/workflows/wf-1/versions/2", "/workflows/wf-1/versions/2/"),
        ("POST", "/workflows/wf-1/draft/", "/workflows/wf-1/draft/"),
        ("POST", "/workflows/wf-1/versions/2/nodes/", "/workflows/wf-1/versions/2/nodes/"),
        ("GET", "/workflows/wf-1/versions/2/nodes/", "/workflows/wf-1/versions/2/nodes/"),
        ("PATCH", "/workflows/wf-1/versions/2/nodes/n-1/", "/workflows/wf-1/versions/2/nodes/n-1/"),
        ("DELETE", "/workflows/wf-1/versions/2/nodes/n-1/", "/workflows/wf-1/versions/2/nodes/n-1/"),
        ("POST", "/workflows/wf-1/versions/2/edges/", "/workflows/wf-1/versions/2/edges/"),
        ("GET", "/workflows/wf-1/versions/2/edges/", "/workflows/wf-1/versions/2/edges/"),
        ("PATCH", "/workflows/wf-1/versions/2/edges/e-1/", "/workflows/wf-1/versions/2/edges/e-1/"),
        ("DELETE", "/workflows/wf-1/versions/2/edges/e-1/", "/workflows/wf-1/versions/2/edges/e-1/"),
        ("POST", "/workflows/wf-1/versions/2/validate/", "/workflows/wf-1/versions/2/validate/"),
        ("POST", "/workflows/wf-1/versions/2/publish/", "/workflows/wf-1/versions/2/publish/"),
        ("POST", "/workflows/wf-1/deactivate/", "/workflows/wf-1/deactivate/"),
        ("POST", "/workflows/wf-1/activate/", "/workflows/wf-1/activate/"),
    ],
)
def test_workflow_routes_proxy_to_workflow_service(
    gateway_client, monkeypatch, method, path, expected_path
):
    calls = fake_upstream(monkeypatch, status_code=207)
    response = gateway_client.request(
        method,
        path,
        json={"payload": "value"} if method in {"POST", "PATCH"} else None,
        headers={"x-client-header": "preserved"},
    )
    assert response.status_code == 207
    forwarded = calls[-1]
    assert urlparse(forwarded["url"]).path.endswith(expected_path)
    assert forwarded["method"] == method
    assert forwarded["headers"]["x-client-header"] == "preserved"


def test_proxy_request_forwards_body_query_and_filters_hop_headers(monkeypatch, gateway_client):
    calls = fake_upstream(
        monkeypatch,
        status_code=201,
        headers={"x-upstream": "yes", "connection": "close", "content-length": "11"},
        content=b'{"created":1}',
    )
    response = gateway_client.post(
        "/auth/login?next=dashboard",
        json={"email": "u@example.com"},
        headers={"connection": "keep-alive", "x-forward": "yes"},
    )
    assert response.status_code == 201
    assert response.json() == {"created": 1}
    forwarded = calls[-1]
    assert forwarded["content"] == b'{"email":"u@example.com"}'
    assert forwarded["params"].get("next") == "dashboard"
    assert forwarded["headers"]["x-forward"] == "yes"
    assert "connection" not in forwarded["headers"]
    assert response.headers["x-upstream"] == "yes"


def test_build_proxy_response_preserves_cookies_and_strips_response_headers():
    downstream = httpx.Response(
        302,
        content=gzip.compress(b"redirect"),
        headers=[
            ("location", "https://frontend.test/login"),
            ("set-cookie", "session=a; Path=/"),
            ("set-cookie", "state=b; Path=/"),
            ("content-encoding", "gzip"),
            ("server", "upstream"),
            ("connection", "close"),
        ],
    )
    response = proxy.build_proxy_response(downstream)
    assert response.status_code == 302
    assert response.body == b"redirect"
    assert response.headers["location"] == "https://frontend.test/login"
    assert response.headers.getlist("set-cookie") == ["session=a; Path=/", "state=b; Path=/"]
    assert "content-encoding" not in response.headers
    assert "server" not in response.headers
    assert "connection" not in response.headers


def test_proxy_request_preserves_redirect_response(gateway_client, monkeypatch):
    calls = fake_upstream(monkeypatch, status_code=302, headers={"location": "https://accounts.google.test"})
    response = gateway_client.get("/auth/google", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://accounts.google.test"
    assert calls[0]["client_options"].get("follow_redirects") is False
