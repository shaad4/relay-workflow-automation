import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import httpx
from fastapi import FastAPI

# Make the service package importable when pytest is started from this folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.dependencies import get_current_user
from app.routes import auth


class InProcessClient:
    def __init__(self, app):
        self.app = app
        self.cookies = httpx.Cookies()

    def request(self, method, path, **kwargs):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self.app),
                base_url="http://testserver",
                cookies=self.cookies,
            ) as client:
                response = await client.request(method, path, **kwargs)
                self.cookies.update(client.cookies)
                return response

        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)


@pytest.fixture
def client(monkeypatch):
    async def noop_email(*_args):
        return None

    monkeypatch.setattr(auth, "send_verification_email", noop_email)
    monkeypatch.setattr(auth, "send_password_reset_email", noop_email)
    app = FastAPI()
    app.include_router(auth.router)

    async def fake_get_db():
        yield object()

    app.dependency_overrides[auth.get_db] = fake_get_db
    async def fake_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = fake_get_current_user
    monkeypatch.setenv("FRONTEND_URL", "https://frontend.example")
    monkeypatch.setattr(
        auth,
        "decode_token",
        lambda _token: {
            "exp": datetime.now(timezone.utc).timestamp() + 7 * 24 * 60 * 60,
            "type": "refresh",
            "sid": "session-id",
        },
    )

    yield InProcessClient(app)


test_user = SimpleNamespace(
    id=uuid4(),
    workspace_id=uuid4(),
    name="Test User",
    email="test@example.com",
    email_verified_at=datetime.now(timezone.utc),
)


def test_register(client, monkeypatch):
    verification_token = SimpleNamespace(token="verify-token")

    async def register_user(data, session):
        return test_user, verification_token

    monkeypatch.setattr(auth, "register_user", register_user)
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": test_user.email,
            "password": "Secure123!",
            "workspace_name": "Test Workspace",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == test_user.email


def test_register_rejects_duplicate_email(client, monkeypatch):
    async def register_user(data, session):
        raise ValueError("Email already registered")

    monkeypatch.setattr(auth, "register_user", register_user)
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": test_user.email,
            "password": "Secure123!",
            "workspace_name": "Test Workspace",
        },
    )

    assert response.status_code == 409


def test_login(client, monkeypatch):
    async def login_user(data, session):
        return "access-token", "refresh-token"

    monkeypatch.setattr(auth, "login_user", login_user)
    response = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "Secure123!"},
    )

    assert response.status_code == 200
    assert response.json() == {"token_type": "bearer"}
    cookies = response.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert any(cookie.startswith("relay_access_token=") and "httponly" in cookie.lower() for cookie in cookies)
    assert any(cookie.startswith("relay_refresh_token=") and "httponly" in cookie.lower() and "path=/auth" in cookie.lower() for cookie in cookies)
    assert "access-token" not in response.text
    assert "refresh-token" not in response.text


def test_login_rejects_invalid_credentials(client, monkeypatch):
    async def login_user(data, session):
        raise ValueError("Invalid email or password")

    monkeypatch.setattr(auth, "login_user", login_user)
    response = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "wrong"},
    )

    assert response.status_code == 401


def test_login_requests_email_verification(client, monkeypatch):
    from app.core.exceptions import EmailVerificationRequired

    async def login_user(data, session):
        raise EmailVerificationRequired(
            token="verify-token",
            user_email=test_user.email,
            user_name=test_user.name,
        )

    monkeypatch.setattr(auth, "login_user", login_user)
    response = client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "Secure123!"},
    )

    assert response.status_code == 401
    assert "verify" in response.json()["detail"].lower()


def test_refresh(client, monkeypatch):
    async def refresh_access_token(token, session):
        assert token == "refresh-token"
        return "new-access-token", "rotated-refresh-token"

    monkeypatch.setattr(auth, "refresh_access_token", refresh_access_token)
    client.cookies.set("relay_refresh_token", "refresh-token", path="/auth")
    response = client.post("/auth/refresh")

    assert response.status_code == 200
    assert response.json() == {"token_type": "bearer"}
    cookies = response.headers.get_list("set-cookie")
    assert any(cookie.startswith("relay_access_token=new-access-token") for cookie in cookies)
    assert any(cookie.startswith("relay_refresh_token=rotated-refresh-token") for cookie in cookies)
    assert "new-access-token" not in response.text
    assert "rotated-refresh-token" not in response.text


def test_refresh_rejects_invalid_token(client, monkeypatch):
    async def refresh_access_token(token, session):
        raise ValueError("Invalid refresh token")

    monkeypatch.setattr(auth, "refresh_access_token", refresh_access_token)
    client.cookies.set("relay_refresh_token", "invalid", path="/auth")
    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert any(
        cookie.startswith("relay_refresh_token=") and "max-age=0" in cookie.lower()
        for cookie in response.headers.get_list("set-cookie")
    )


def test_me_and_logout(client):
    me = client.get("/auth/me")
    logout = client.post("/auth/logout")

    assert me.status_code == 200
    assert me.json()["id"] == str(test_user.id)
    assert logout.status_code == 200
    assert logout.json() == {"message": "Logged out successfully"}


def test_logout_revokes_refresh_session_and_clears_both_cookies(client, monkeypatch):
    revoked = []

    async def revoke_refresh_session(session_id, session):
        revoked.append(session_id)
        return True

    monkeypatch.setattr(auth, "revoke_refresh_session", revoke_refresh_session)
    client.cookies.set("relay_refresh_token", "refresh-token", path="/auth")
    client.cookies.set("relay_access_token", "access-token", path="/")

    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert revoked == ["session-id"]
    cleared = response.headers.get_list("set-cookie")
    assert any(cookie.startswith("relay_access_token=") and "max-age=0" in cookie.lower() for cookie in cleared)
    assert any(cookie.startswith("relay_refresh_token=") and "max-age=0" in cookie.lower() for cookie in cleared)


def test_verify_email(client, monkeypatch):
    async def verify_email_token(token, session):
        return None

    monkeypatch.setattr(auth, "verify_email_token", verify_email_token)
    response = client.get("/auth/verify-email?token=verify-token")

    assert response.status_code == 200
    assert response.json() == {"message": "Email verified successfully"}


def test_verify_email_rejects_invalid_token(client, monkeypatch):
    async def verify_email_token(token, session):
        raise ValueError("Invalid verification token")

    monkeypatch.setattr(auth, "verify_email_token", verify_email_token)
    response = client.get("/auth/verify-email?token=invalid")

    assert response.status_code == 400


def test_resend_verification(client, monkeypatch):
    async def resend_verification_email(email, session):
        return None

    monkeypatch.setattr(auth, "resend_verification_email", resend_verification_email)
    response = client.post(
        "/auth/resend-verification", json={"email": test_user.email}
    )

    assert response.status_code == 200
    assert "If an account" in response.json()["message"]


def test_forgot_password(client, monkeypatch):
    async def create_password_reset_token(email, session):
        return None

    monkeypatch.setattr(auth, "create_password_reset_token", create_password_reset_token)
    response = client.post(
        "/auth/forgot-password", json={"email": test_user.email}
    )

    assert response.status_code == 200
    assert "If an account" in response.json()["message"]


def test_reset_password(client, monkeypatch):
    async def reset_password(token, new_password, session):
        return None

    monkeypatch.setattr(auth, "reset_password", reset_password)
    response = client.post(
        "/auth/reset-password",
        json={"token": "reset-token", "new_password": "Secure123!"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password reset successfully"}


def test_reset_password_rejects_invalid_token(client, monkeypatch):
    async def reset_password(token, new_password, session):
        raise ValueError("Invalid reset token")

    monkeypatch.setattr(auth, "reset_password", reset_password)
    response = client.post(
        "/auth/reset-password",
        json={"token": "invalid", "new_password": "Secure123!"},
    )

    assert response.status_code == 400


def test_google_login_redirects_and_sets_state_cookie(client, monkeypatch):
    monkeypatch.setattr(
        auth,
        "create_google_authorization_url",
        lambda: ("https://accounts.google.test/authorize", "state-value"),
    )

    response = client.get("/auth/google", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "https://accounts.google.test/authorize"
    assert "google_oauth_state=state-value" in response.headers["set-cookie"]


def test_google_callback_validates_state(client):
    missing = client.get("/auth/google/callback?state=state-value")
    client.cookies.set("google_oauth_state", "state-value")
    invalid = client.get(
        "/auth/google/callback?state=wrong",
    )

    assert missing.status_code == 400
    assert invalid.status_code == 400


def test_google_callback_redirects_on_provider_error(client):
    client.cookies.set("google_oauth_state", "state-value")
    response = client.get(
        "/auth/google/callback?state=state-value&error=access_denied",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "https://frontend.example/login"


def test_google_callback_requires_code(client):
    client.cookies.set("google_oauth_state", "state-value")
    response = client.get(
        "/auth/google/callback?state=state-value",
    )

    assert response.status_code == 400


@pytest.mark.parametrize("existing_user", [True, False])
def test_google_callback_redirects_to_login_exchange_or_signup(
    client, monkeypatch, existing_user
):
    user = test_user if existing_user else None
    login_session = SimpleNamespace(id=uuid4())
    signup_session = SimpleNamespace(id=uuid4())

    async def exchange_google_code(code):
        return {"access_token": "google-access"}

    async def get_google_userinfo(access_token):
        return {"sub": "google-id", "email": test_user.email, "name": test_user.name}

    async def find_google_user(google_id, email, session):
        return user

    async def create_google_login_session(user_id, session):
        return login_session

    async def create_google_signup_session(google_id, email, name, session):
        return signup_session

    monkeypatch.setattr(auth, "exchange_google_code", exchange_google_code)
    monkeypatch.setattr(auth, "get_google_userinfo", get_google_userinfo)
    monkeypatch.setattr(auth, "find_google_user", find_google_user)
    monkeypatch.setattr(auth, "create_google_login_session", create_google_login_session)
    monkeypatch.setattr(auth, "create_google_signup_session", create_google_signup_session)

    client.cookies.set("google_oauth_state", "state-value")
    response = client.get(
        "/auth/google/callback?state=state-value&code=google-code",
        follow_redirects=False,
    )

    assert response.status_code == 307
    if existing_user:
        assert response.headers["location"].endswith(
            f"/auth/google/callback?code={login_session.id}"
        )
    else:
        assert response.headers["location"].endswith(
            f"/workspace-setup?session={signup_session.id}"
        )


def test_google_exchange(client, monkeypatch):
    async def consume_google_login_session(login_session_id, session):
        return "access-token", "refresh-token"

    monkeypatch.setattr(auth, "consume_google_login_session", consume_google_login_session)
    response = client.post("/auth/google/exchange", json={"code": str(uuid4())})

    assert response.status_code == 200
    assert response.json() == {"token_type": "bearer"}
    assert len(response.headers.get_list("set-cookie")) == 2


def test_google_exchange_rejects_invalid_session(client, monkeypatch):
    async def consume_google_login_session(login_session_id, session):
        raise ValueError("Invalid login session")

    monkeypatch.setattr(auth, "consume_google_login_session", consume_google_login_session)
    response = client.post("/auth/google/exchange", json={"code": str(uuid4())})

    assert response.status_code == 400


def test_google_signup_completion(client, monkeypatch):
    async def complete_google_signup(signup_session_id, workspace_name, session):
        return test_user, "access-token", "refresh-token"

    monkeypatch.setattr(auth, "complete_google_signup", complete_google_signup)
    response = client.post(
        "/auth/google/complete",
        json={"signup_session_id": str(uuid4()), "workspace_name": "Workspace"},
    )

    assert response.status_code == 200
    assert response.json() == {"token_type": "bearer"}
    assert len(response.headers.get_list("set-cookie")) == 2


def test_google_signup_completion_rejects_invalid_session(client, monkeypatch):
    async def complete_google_signup(signup_session_id, workspace_name, session):
        raise ValueError("Invalid signup session")

    monkeypatch.setattr(auth, "complete_google_signup", complete_google_signup)
    response = client.post(
        "/auth/google/complete",
        json={"signup_session_id": str(uuid4()), "workspace_name": "Workspace"},
    )

    assert response.status_code == 400
