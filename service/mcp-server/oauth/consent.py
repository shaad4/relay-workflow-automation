import secrets
from html import escape

from starlette.requests import Request
from starlette.responses import HTMLResponse

from oauth.storage import AuthorizationStore


def create_consent_page(store: AuthorizationStore):

    async def consent_page(request: Request):
        request_id = request.query_params.get("request_id")

        if not request_id:
            return HTMLResponse(
                "Missing authorization request",
                status_code=400,
            )

        pending = store.get(request_id)

        if pending is None:
            return HTMLResponse(
                "Authorization request expired or invalid",
                status_code=400,
            )

        # ----------------------------------------
        # Browser Session Binding
        # ----------------------------------------

        session_request_id = request.session.get("oauth_request_id")

        if session_request_id is None:
            request.session["oauth_request_id"] = request_id
            request.session["csrf_token"] = secrets.token_urlsafe(32)

        elif session_request_id != request_id:
            if store.get(session_request_id) is not None:
                return HTMLResponse(
                    "Another authorization request is already active", status_code=400
                )
            request.app.state.login_store.sessions.pop(
                request.session.get("relay_login_session"), None
            )
            request.session.clear()
            request.session["oauth_request_id"] = request_id
            request.session["csrf_token"] = secrets.token_urlsafe(32)

        csrf_token = escape(
            request.session["csrf_token"],
            quote=True,
        )

        safe_request_id = escape(
            request_id,
            quote=True,
        )

        # ----------------------------------------
        # Prepare Consent Information
        # ----------------------------------------

        client_id = escape(pending.client_id)
        scopes = pending.params.scopes or []

        permissions = "".join(f"<li>{escape(scope)}</li>" for scope in scopes)

        if not permissions:
            permissions = "<li>No specific permissions requested</li>"

        # ----------------------------------------
        # Check Authenticated Relay Session
        # ----------------------------------------

        login_id = request.session.get("relay_login_session")

        login_store = request.app.state.login_store

        login_session = login_store.get(login_id) if login_id else None

        # ----------------------------------------
        # Render Login or Approval Form
        # ----------------------------------------

        if login_session:
            action_html = f"""
            <h3>Authorize Relay Access</h3>

            <p>
                You are signed in to Relay.
                Review the permissions before continuing.
            </p>

            <form method="POST" action="/oauth/approve">
                <input
                    type="hidden"
                    name="request_id"
                    value="{safe_request_id}"
                >

                <input
                    type="hidden"
                    name="csrf_token"
                    value="{csrf_token}"
                >

                <button
                    type="submit"
                    name="decision"
                    value="approve"
                >
                    Approve Access
                </button>

                <button
                    type="submit"
                    name="decision"
                    value="deny"
                >
                    Deny
                </button>
            </form>
            """
        else:
            action_html = f"""
            <h3>Sign in to Relay</h3>

            <form method="POST" action="/oauth/login">
                <input
                    type="hidden"
                    name="request_id"
                    value="{safe_request_id}"
                >

                <input
                    type="hidden"
                    name="csrf_token"
                    value="{csrf_token}"
                >

                <label for="email">Email</label>
                <input
                    id="email"
                    type="email"
                    name="email"
                    required
                    autocomplete="username"
                >

                <label for="password">Password</label>
                <input
                    id="password"
                    type="password"
                    name="password"
                    required
                    autocomplete="current-password"
                >

                <button type="submit">
                    Sign in
                </button>
            </form>
            """

        # ----------------------------------------
        # Render Consent Page
        # ----------------------------------------

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >
            <title>Connect to Relay</title>
        </head>

        <body>
            <h2>Connect to Relay</h2>

            <p>
                Application: <strong>{client_id}</strong>
            </p>

            <p>Requested permissions:</p>

            <ul>
                {permissions}
            </ul>

            {action_html}

        </body>
        </html>
        """

        return HTMLResponse(html)

    return consent_page
