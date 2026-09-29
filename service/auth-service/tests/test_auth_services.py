import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import dependencies, jwt as jwt_service, security
from app.core.exceptions import EmailVerificationRequired
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service, token_sessions, email_verification_service as verification
from app.services import password_reset_service as password_reset
from app.services import google_login, google_oauth, google_signup


class Result:
    def __init__(self, scalar=None):
        self.scalar = scalar

    def scalar_one_or_none(self):
        return self.scalar


class FakeSession:
    def __init__(self, results=()):
        self.results = iter(results)
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.refreshes = 0
        self.deleted = []

    async def execute(self, _statement):
        return next(self.results)

    def add(self, value):
        self.added.append(value)
        if getattr(value, "id", None) is None:
            value.id = uuid4()

    async def flush(self):
        self.flushes += 1
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid4()

    async def commit(self):
        self.commits += 1

    async def refresh(self, _value):
        self.refreshes += 1

    async def delete(self, value):
        self.deleted.append(value)


def test_jwt_and_password_helpers(monkeypatch):
    monkeypatch.setattr(jwt_service, "JWT_SECRET_KEY", "unit-test-secret-that-is-long-enough")
    access = jwt_service.create_access_token({"sub": "user-1"})
    refresh = jwt_service.create_refresh_token({"sub": "user-1"})
    assert jwt_service.decode_token(access)["type"] == "access"
    assert jwt_service.decode_token(refresh)["type"] == "refresh"
    with pytest.raises(jwt.InvalidTokenError):
        jwt_service.decode_token("not-a-token")

    password_hash = security.hash_password("Secure123!")
    assert security.verify_password("Secure123!", password_hash)
    assert not security.verify_password("wrong", password_hash)
    assert not security.verify_password("password", "invalid-hash")


def test_register_user_creates_workspace_user_and_verification(monkeypatch):
    async def create_verification_token(user_id, session):
        return SimpleNamespace(user_id=user_id, token="verify-token")

    monkeypatch.setattr(auth_service, "hash_password", lambda password: "hashed")
    monkeypatch.setattr(auth_service, "create_verification_token", create_verification_token)
    session = FakeSession([Result()])
    data = RegisterRequest(
        name="Test User",
        email="test@example.com",
        password="Secure123!",
        workspace_name="Test Workspace",
    )
    user, token = asyncio.run(auth_service.register_user(data, session))
    assert user.email == data.email
    assert user.password_hash == "hashed"
    assert session.flushes == 2
    assert session.commits == 1
    assert token.token == "verify-token"


def test_login_user_validates_credentials_and_verification(monkeypatch):
    unverified = SimpleNamespace(
        id=uuid4(), workspace_id=uuid4(), email="user@example.com", name="User",
        password_hash="stored", email_verified_at=None,
    )
    monkeypatch.setattr(auth_service, "verify_password", lambda password, hashed: True)
    async def create_verification_token(user_id, session):
        return SimpleNamespace(token="verify-token")
    monkeypatch.setattr(auth_service, "create_verification_token", create_verification_token)
    session = FakeSession([Result(unverified)])
    with pytest.raises(EmailVerificationRequired):
        asyncio.run(auth_service.login_user(LoginRequest(email=unverified.email, password="Secure123!"), session))
    assert session.commits == 1

    verified = SimpleNamespace(**{**vars(unverified), "email_verified_at": datetime.now(timezone.utc)})
    async def create_refresh_session(user_id, workspace_id, session):
        return "access", "refresh"

    monkeypatch.setattr(auth_service, "create_refresh_session", create_refresh_session)
    session = FakeSession([Result(verified)])
    assert asyncio.run(auth_service.login_user(LoginRequest(email=verified.email, password="Secure123!"), session)) == ("access", "refresh")


@pytest.mark.parametrize("user", [None, SimpleNamespace(password_hash="stored")])
def test_login_user_rejects_missing_user_or_bad_password(monkeypatch, user):
    monkeypatch.setattr(auth_service, "verify_password", lambda password, hashed: False)
    session = FakeSession([Result(user)])
    with pytest.raises(ValueError, match="Invalid email or password"):
        asyncio.run(auth_service.login_user(LoginRequest(email="u@example.com", password="bad"), session))


def test_refresh_access_token_checks_token_type(monkeypatch):
    calls = []

    async def rotate_refresh_token(token, session):
        calls.append((token, session))
        return "new-access", "new-refresh"

    monkeypatch.setattr(auth_service, "rotate_refresh_token", rotate_refresh_token)
    session = object()
    assert asyncio.run(auth_service.refresh_access_token("valid-refresh", session)) == (
        "new-access",
        "new-refresh",
    )
    assert calls == [("valid-refresh", session)]


def test_create_refresh_session_uses_fixed_session_expiry(monkeypatch):
    monkeypatch.setattr(token_sessions, "create_access_token", lambda claims: ("access", claims))
    monkeypatch.setattr(token_sessions, "create_refresh_token", lambda claims, expires_at: ("refresh", claims, expires_at))
    session = FakeSession()

    access, refresh = asyncio.run(
        token_sessions.create_refresh_session(uuid4(), uuid4(), session)
    )

    assert access[0] == "access"
    assert refresh[0] == "refresh"
    row = session.added[0]
    assert row.expires_at > datetime.now(timezone.utc)
    assert refresh[2] == row.expires_at
    assert access[1]["sid"] == str(row.id)
    assert refresh[1]["sid"] == str(row.id)
    assert session.flushes == 1


def test_rotate_refresh_token_rotates_jti_without_extending_session(monkeypatch):
    session_id = uuid4()
    user_id = uuid4()
    workspace_id = uuid4()
    current_id = uuid4()
    next_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=3)
    row = SimpleNamespace(
        id=session_id,
        user_id=user_id,
        current_token_id=str(current_id),
        expires_at=expires_at,
        revoked_at=None,
    )
    monkeypatch.setattr(
        token_sessions,
        "decode_token",
        lambda _token: {
            "type": "refresh",
            "sid": str(session_id),
            "sub": str(user_id),
            "workspace_id": str(workspace_id),
            "jti": str(current_id),
        },
    )
    monkeypatch.setattr(token_sessions.uuid, "uuid4", lambda: next_id)
    monkeypatch.setattr(token_sessions, "create_access_token", lambda claims: ("access", claims))
    monkeypatch.setattr(token_sessions, "create_refresh_token", lambda claims, expires_at: ("refresh", claims, expires_at))
    session = FakeSession([Result(row)])

    access, refresh = asyncio.run(token_sessions.rotate_refresh_token("current", session))

    assert row.current_token_id == str(next_id)
    assert session.commits == 1
    assert access[1]["sid"] == str(session_id)
    assert refresh[1]["jti"] == str(next_id)
    assert refresh[2] == expires_at


def test_rotate_refresh_token_reuse_revokes_session(monkeypatch):
    row = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        current_token_id=str(uuid4()),
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        revoked_at=None,
    )
    monkeypatch.setattr(
        token_sessions,
        "decode_token",
        lambda _token: {
            "type": "refresh",
            "sid": str(row.id),
            "sub": str(row.user_id),
            "workspace_id": str(uuid4()),
            "jti": str(uuid4()),
        },
    )
    session = FakeSession([Result(row)])

    with pytest.raises(ValueError, match="reuse detected"):
        asyncio.run(token_sessions.rotate_refresh_token("reused", session))

    assert row.revoked_at is not None
    assert session.commits == 1


def test_verification_token_success_and_failure_paths(monkeypatch):
    user = SimpleNamespace(id=uuid4(), email_verified_at=None)
    token = SimpleNamespace(user_id=user.id, used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
    session = FakeSession([Result(token), Result(user)])
    asyncio.run(verification.verify_email_token("token", session))
    assert user.email_verified_at is not None
    assert token.used_at is not None
    assert session.commits == 1

    for token_row, message in [
        (None, "Invalid verification token"),
        (SimpleNamespace(used_at=datetime.now(timezone.utc)), "already been used"),
        (SimpleNamespace(used_at=None, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)), "expired"),
    ]:
        with pytest.raises(ValueError, match=message):
            asyncio.run(verification.verify_email_token("bad", FakeSession([Result(token_row)])))


def test_resend_verification_skips_unknown_or_verified_user(monkeypatch):
    for user in (None, SimpleNamespace(email_verified_at=datetime.now(timezone.utc))):
        assert asyncio.run(verification.resend_verification_email("u@example.com", FakeSession([Result(user)]))) is None


def test_create_and_resend_verification_tokens():
    user = SimpleNamespace(id=uuid4(), email="u@example.com", email_verified_at=None, name="User")
    session = FakeSession([Result(user), Result()])
    token = asyncio.run(verification.create_verification_token(user.id, session))
    assert token.user_id == user.id
    assert token.token
    assert token.expires_at > datetime.now(timezone.utc)

    session = FakeSession([Result(user), Result()])
    resent_token, returned_user = asyncio.run(
        verification.resend_verification_email(user.email, session)
    )
    assert returned_user is user
    assert resent_token.user_id == user.id
    assert session.commits == 1


def test_password_reset_validation_and_success(monkeypatch):
    user = SimpleNamespace(id=uuid4(), password_hash="old")
    token = SimpleNamespace(user_id=user.id, used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
    session = FakeSession([Result(token), Result(user), Result()])
    monkeypatch.setattr(password_reset, "hash_password", lambda password: "new-hash")
    asyncio.run(password_reset.reset_password("token", "Secure123!", session))
    assert user.password_hash == "new-hash"
    assert token.used_at is not None
    assert session.commits == 1

    bad_cases = [
        (None, None, "Invalid password reset token"),
        (SimpleNamespace(used_at=datetime.now(timezone.utc)), None, "already been used"),
        (SimpleNamespace(used_at=None, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)), None, "expired"),
        (SimpleNamespace(user_id=uuid4(), used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=1)), None, "User not found"),
    ]
    for token_row, reset_user, message in bad_cases:
        results = [Result(token_row)]
        if token_row is not None and getattr(token_row, "expires_at", None) is not None:
            results.append(Result(reset_user))
        with pytest.raises(ValueError, match=message):
            asyncio.run(password_reset.reset_password("bad", "Secure123!", FakeSession(results)))


def test_create_password_reset_token_for_existing_user():
    user = SimpleNamespace(id=uuid4(), email="u@example.com")
    session = FakeSession([Result(user), Result()])
    token, returned_user = asyncio.run(
        password_reset.create_password_reset_token(user.email, session)
    )
    assert returned_user is user
    assert token.user_id == user.id
    assert token.token
    assert token.expires_at > datetime.now(timezone.utc)
    assert session.commits == 1
    assert session.refreshes == 1

    assert asyncio.run(
        password_reset.create_password_reset_token("missing@example.com", FakeSession([Result()]))
    ) is None


def test_current_token_and_current_user_dependency(monkeypatch):
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    monkeypatch.setattr(dependencies, "decode_token", lambda token: {"type": "access", "sub": str(uuid4())})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    assert asyncio.run(dependencies.get_current_token(credentials))["type"] == "access"
    assert asyncio.run(
        dependencies.get_current_token(None, access_cookie="cookie-token")
    )["type"] == "access"

    for decode, message in [
        (lambda token: (_ for _ in ()).throw(jwt.ExpiredSignatureError()), "expired"),
        (lambda token: (_ for _ in ()).throw(jwt.InvalidTokenError()), "Invalid access token"),
        (lambda token: {"type": "refresh", "sub": "user"}, "Invalid access token"),
        (lambda token: {"type": "access"}, "Invalid access token"),
    ]:
        monkeypatch.setattr(dependencies, "decode_token", decode)
        with pytest.raises(HTTPException, match=message):
            asyncio.run(dependencies.get_current_token(credentials))

    user_id = uuid4()
    user = SimpleNamespace(id=user_id)
    session = FakeSession([Result(user)])
    assert asyncio.run(dependencies.get_current_user({"sub": str(user_id)}, session)) is user

    with pytest.raises(HTTPException, match="Invalid access token"):
        asyncio.run(dependencies.get_current_user({"sub": "not-uuid"}, FakeSession()))
    with pytest.raises(HTTPException, match="User not found"):
        asyncio.run(dependencies.get_current_user({"sub": str(uuid4())}, FakeSession([Result()])))


def test_google_login_session_create_consume_and_invalid(monkeypatch):
    user_id = uuid4()
    user = SimpleNamespace(id=user_id, workspace_id=uuid4())
    async def create_refresh_session(user_id, workspace_id, session):
        return "access", "refresh"

    monkeypatch.setattr(google_login, "create_refresh_session", create_refresh_session)

    created_session = FakeSession()
    login_session = asyncio.run(google_login.create_google_login_session(user_id, created_session))
    assert login_session.user_id == user_id
    assert created_session.commits == 1

    consumed = SimpleNamespace(id=login_session.id, user_id=user_id, used_at=None,
                               expires_at=datetime.now(timezone.utc) + timedelta(minutes=2))
    session = FakeSession([Result(consumed), Result(user)])
    assert asyncio.run(google_login.consume_google_login_session(login_session.id, session)) == ("access", "refresh")
    assert consumed.used_at is not None
    assert session.commits == 1

    for row, expected in [
        (None, "Invalid Google login session"),
        (SimpleNamespace(used_at=datetime.now(timezone.utc)), "already been used"),
        (SimpleNamespace(used_at=None, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)), "expired"),
    ]:
        with pytest.raises(ValueError, match=expected):
            asyncio.run(google_login.consume_google_login_session(uuid4(), FakeSession([Result(row)])))


def test_google_signup_session_complete_and_rejections(monkeypatch):
    session_row = SimpleNamespace(
        id=uuid4(), google_id="google-1", email="new@example.com", name="New User",
        used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    monkeypatch.setattr(google_signup, "hash_password", lambda password: "hashed")
    async def create_refresh_session(user_id, workspace_id, session):
        return "access", "refresh"

    monkeypatch.setattr(google_signup, "create_refresh_session", create_refresh_session)

    session = FakeSession([Result(session_row), Result(), Result()])
    user, access, refresh = asyncio.run(
        google_signup.complete_google_signup(session_row.id, "  My Workspace  ", session)
    )
    assert access == "access" and refresh == "refresh"
    assert user.email == session_row.email
    assert user.google_id == session_row.google_id
    assert session_row.used_at is not None
    assert session.commits == 1


def test_create_google_signup_session():
    created = asyncio.run(
        google_signup.create_google_signup_session(
            "google-id", "new@example.com", "New User", FakeSession()
        )
    )
    assert created.google_id == "google-id"
    assert created.email == "new@example.com"
    assert created.name == "New User"
    assert created.expires_at > datetime.now(timezone.utc)

    for row, name, expected in [
        (None, "Workspace", "Invalid Google signup session"),
        (SimpleNamespace(used_at=datetime.now(timezone.utc)), "Workspace", "already been used"),
        (SimpleNamespace(used_at=None, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)), "Workspace", "expired"),
        (SimpleNamespace(used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=1)), " ", "Workspace name is required"),
        (SimpleNamespace(used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=1)), "A", "at least 2 characters"),
        (SimpleNamespace(used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=1)), "x" * 101, "100 characters or fewer"),
    ]:
        with pytest.raises(ValueError, match=expected):
            asyncio.run(google_signup.complete_google_signup(uuid4(), name, FakeSession([Result(row)])))


def test_google_signup_rejects_existing_account():
    session_row = SimpleNamespace(
        id=uuid4(), google_id="google-1", email="new@example.com", name="New",
        used_at=None, expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    session = FakeSession([Result(session_row), Result(SimpleNamespace(id=uuid4()))])
    with pytest.raises(ValueError, match="already registered"):
        asyncio.run(google_signup.complete_google_signup(session_row.id, "Workspace", session))


def test_google_oauth_url_find_user_and_missing_settings(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://relay.test/callback")
    url, state = google_oauth.create_google_authorization_url()
    assert "client_id=client-id" in url
    assert f"state={state}" in url

    monkeypatch.delenv("GOOGLE_CLIENT_ID")
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        google_oauth.create_google_authorization_url()

    linked_user = SimpleNamespace(id=uuid4())
    assert asyncio.run(google_oauth.find_google_user("gid", "email", FakeSession([Result(linked_user)]))) is linked_user
    by_email = SimpleNamespace(id=uuid4())
    assert asyncio.run(google_oauth.find_google_user("gid", "email", FakeSession([Result(), Result(by_email)]))) is by_email


def test_email_sending_renders_template_and_sends(monkeypatch):
    from app.services import email_service

    sent = []

    class SMTP:
        def __init__(self, host, port):
            assert host == "smtp.test"
            assert port == 2525

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            assert (username, password) == ("mailer", "secret")

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr(email_service, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(email_service, "SMTP_PORT", 2525)
    monkeypatch.setattr(email_service, "SMTP_USERNAME", "mailer")
    monkeypatch.setattr(email_service, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(email_service, "SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr(email_service, "FRONTEND_URL", "https://frontend.test")
    monkeypatch.setattr(email_service.smtplib, "SMTP", SMTP)
    email_service.send_verification_email("u@example.com", "User", "verify", 30)
    email_service.send_password_reset_email("u@example.com", "User", "reset", 30)
    assert len(sent) == 2
    assert "https://frontend.test/verify-email?token=verify" in sent[0].get_body("html").get_content()
    assert "https://frontend.test/reset-password?token=reset" in sent[1].get_body("html").get_content()


def test_email_send_reraises_smtp_error(monkeypatch):
    from app.services import email_service

    class BrokenSMTP:
        def __init__(self, *_args):
            raise OSError("SMTP unavailable")

    monkeypatch.setattr(email_service, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(email_service, "SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr(email_service, "FRONTEND_URL", "https://frontend.test")
    monkeypatch.setattr(email_service.smtplib, "SMTP", BrokenSMTP)
    with pytest.raises(OSError, match="SMTP unavailable"):
        email_service.send_verification_email("u@example.com", "User", "token", 30)


def test_google_oauth_exchange_and_userinfo(monkeypatch):
    class Response:
        is_success = True
        text = ""

        def json(self):
            return {"access_token": "google-access", "email": "u@example.com"}

    class AsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url, data):
            assert url == google_oauth.GOOGLE_TOKEN_URL
            assert data["code"] == "oauth-code"
            return Response()

        async def get(self, url, headers):
            assert url == google_oauth.GOOGLE_USERINFO_URL
            assert headers["Authorization"] == "Bearer google-access"
            return Response()

    monkeypatch.setattr(google_oauth.httpx, "AsyncClient", AsyncClient)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://relay.test/callback")
    tokens = asyncio.run(google_oauth.exchange_google_code("oauth-code"))
    profile = asyncio.run(google_oauth.get_google_userinfo(tokens["access_token"]))
    assert tokens["access_token"] == "google-access"
    assert profile["email"] == "u@example.com"


def test_google_oauth_reports_failed_http_responses(monkeypatch):
    class Response:
        is_success = False
        text = "provider error"

    class AsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            return Response()

        async def get(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(google_oauth.httpx, "AsyncClient", AsyncClient)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://relay.test/callback")
    with pytest.raises(RuntimeError, match="token exchange failed"):
        asyncio.run(google_oauth.exchange_google_code("code"))
    with pytest.raises(RuntimeError, match="userinfo request failed"):
        asyncio.run(google_oauth.get_google_userinfo("token"))


def test_google_oauth_exchange_requires_settings(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        asyncio.run(google_oauth.exchange_google_code("code"))
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_SECRET"):
        asyncio.run(google_oauth.exchange_google_code("code"))
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    with pytest.raises(RuntimeError, match="GOOGLE_REDIRECT_URI"):
        asyncio.run(google_oauth.exchange_google_code("code"))


def test_grpc_auth_server_validates_tokens_and_resolves_workspace(monkeypatch):
    from app.grpc import auth_server
    from app.grpc.generated.auth import auth_pb2

    service = auth_server.AuthInternalService()
    monkeypatch.setattr(auth_server, "decode_token", lambda token: {"type": "access", "sub": "u", "workspace_id": "w"})
    valid = asyncio.run(service.ValidateToken(auth_pb2.ValidateTokenRequest(access_token="good"), None))
    assert valid.valid and valid.user_id == "u" and valid.workspace_id == "w"

    monkeypatch.setattr(auth_server, "decode_token", lambda token: {"type": "refresh", "sub": "u", "workspace_id": "w"})
    assert not asyncio.run(service.ValidateToken(auth_pb2.ValidateTokenRequest(access_token="refresh"), None)).valid
    monkeypatch.setattr(auth_server, "decode_token", lambda token: {"type": "access", "sub": "u"})
    assert not asyncio.run(service.ValidateToken(auth_pb2.ValidateTokenRequest(access_token="missing-workspace"), None)).valid
    monkeypatch.setattr(auth_server, "decode_token", lambda token: (_ for _ in ()).throw(jwt.InvalidTokenError()))
    assert not asyncio.run(service.ValidateToken(auth_pb2.ValidateTokenRequest(access_token="bad"), None)).valid

    class SessionContext:
        async def __aenter__(self):
            return FakeSession([Result(SimpleNamespace(workspace_id=uuid4()))])

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(auth_server, "AsyncSessionLocal", SessionContext)
    found = asyncio.run(service.ResolveWorkspace(auth_pb2.ResolveWorkspaceRequest(user_id="u"), None))
    assert found.found

    class MissingSessionContext:
        async def __aenter__(self):
            return FakeSession([Result()])

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(auth_server, "AsyncSessionLocal", MissingSessionContext)
    missing = asyncio.run(service.ResolveWorkspace(auth_pb2.ResolveWorkspaceRequest(user_id="missing"), None))
    assert not missing.found


def test_grpc_server_startup(monkeypatch):
    from app.grpc import server as grpc_server

    calls = []

    class Server:
        def add_insecure_port(self, address):
            calls.append(("port", address))

        async def start(self):
            calls.append(("start",))

    fake_server = Server()
    monkeypatch.setattr(grpc_server.grpc.aio, "server", lambda: fake_server)
    monkeypatch.setattr(
        grpc_server.auth_pb2_grpc,
        "add_AuthInternalServiceServicer_to_server",
        lambda service, server: calls.append(("register", isinstance(service, grpc_server.AuthInternalService))),
    )
    result = asyncio.run(grpc_server.start_grpc_server())
    assert result is fake_server
    assert calls == [("register", True), ("port", "[::]:50051"), ("start",)]


def test_app_health_and_lifespan(monkeypatch):
    from app import main

    class GrpcServer:
        def __init__(self):
            self.stopped = None

        async def stop(self, grace):
            self.stopped = grace

    grpc_server = GrpcServer()

    async def start_server():
        return grpc_server

    monkeypatch.setattr(main, "start_grpc_server", start_server)

    async def exercise():
        async with main.lifespan(main.app):
            assert main.health_check() == {"status": "ok"}
        assert grpc_server.stopped == 5

    asyncio.run(exercise())
