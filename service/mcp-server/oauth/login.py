import os
import secrets
import time

import httpx
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from user_session import UserRelaySession

from oauth.relay_auth import authenticate_relay_user
from oauth.security import validate_csrf
from oauth.storage import AuthorizationStore


class LoginStore:
    def __init__(self):
        self.sessions = {}

    def cleanup(self):
        now = time.time()
        self.sessions = {k: v for k, v in self.sessions.items() if v["expires_at"] > now}

    def save(self, identity: dict) -> str:
        self.cleanup()
        session_id = secrets.token_urlsafe(32)

        self.sessions[session_id] = {
            "identity": {k: identity[k] for k in ("user_id", "workspace_id")},
            "relay_session": UserRelaySession(
                os.environ["RELAY_API_URL"],
                identity["access_token"],
                identity["refresh_token"],
                user_id=str(identity["user_id"]),
                workspace_id=str(identity["workspace_id"]),
            ),
            "expires_at": time.time() + 600,
        }

        return session_id

    def get(self, session_id: str):
        session = self.sessions.get(session_id)

        if not session:
            return None

        if session["expires_at"] <= time.time():
            self.sessions.pop(session_id, None)
            return None

        return session


def create_login_handler(
    authorization_store: AuthorizationStore,
    login_store: LoginStore,
    public_origin: str,
):

    async def login(request: Request):
        origin = request.headers.get("origin")
        expected_origin = public_origin

        if origin != expected_origin:
            return HTMLResponse(
                "Invalid request origin",
                status_code=403,
            )

        form = await request.form()

        request_id = str(form.get("request_id", ""))
        csrf_token = str(form.get("csrf_token", ""))
        email = str(form.get("email", ""))
        password = str(form.get("password", ""))

        if request.session.get("oauth_request_id") != request_id or not validate_csrf(
            request, csrf_token
        ):
            return HTMLResponse(
                "Invalid authorization session",
                status_code=403,
            )

        pending = authorization_store.get(request_id)

        if pending is None:
            return HTMLResponse(
                "Authorization request expired",
                status_code=400,
            )

        try:
            identity = await authenticate_relay_user(
                email=email,
                password=password,
            )
        except (httpx.HTTPError, RuntimeError, ValueError):
            return HTMLResponse(
                "Invalid login or authentication unavailable",
                status_code=401,
            )

        login_store.sessions.pop(request.session.get("relay_login_session"), None)
        session_id = login_store.save(identity)
        request.session["csrf_token"] = secrets.token_urlsafe(32)

        request.session["relay_login_session"] = session_id

        return RedirectResponse(
            url=f"/oauth/consent?request_id={request_id}",
            status_code=303,
        )

    return login
