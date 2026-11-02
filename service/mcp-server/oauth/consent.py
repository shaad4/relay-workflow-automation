import secrets
from html import escape
from urllib.parse import quote, urlsplit

from starlette.requests import Request
from starlette.responses import HTMLResponse

from oauth.storage import AuthorizationStore

HTML_CSP = (
    "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)


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

        session_request_id = request.session.get("oauth_request_id")

        if session_request_id is None:
            request.session["oauth_request_id"] = request_id
            request.session["csrf_token"] = secrets.token_urlsafe(32)

        elif session_request_id != request_id:
            if store.get(session_request_id) is not None:
                return HTMLResponse(
                    "Another authorization request is already active",
                    status_code=400,
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
        safe_request_id = escape(request_id, quote=True)
        client_id = escape(pending.client_id)
        client = await request.app.state.provider.get_client(pending.client_id)
        application_name = escape((client.client_name if client else None) or pending.client_id)

        scopes = pending.params.scopes or []

        scope_labels = {
            "relay:read": "View workflows and execution history",
            "relay:write": "Create and modify workflows",
            "relay:execute": "Publish and execute workflows",
            "relay:delete": "Delete workflows and nodes",
        }

        permissions = "".join(
            f'<div class="permission">'
            f'<span class="permission-icon" aria-hidden="true">&#10003;</span>'
            f"<span>{escape(scope_labels.get(scope, scope))}</span>"
            f"</div>"
            for scope in scopes
        )

        if not permissions:
            permissions = '<p class="muted">No specific permissions requested.</p>'

        login_id = request.session.get("relay_login_session")

        login_store = request.app.state.login_store

        login_session = login_store.get(login_id) if login_id else None

        hidden_fields = f"""
            <input type="hidden" name="request_id"
                   value="{safe_request_id}">
            <input type="hidden" name="csrf_token"
                   value="{csrf_token}">
        """

        connection_html = f"""
            <section class="connection" aria-label="Connection details">
                <h2 class="connection-title">Application requesting access</h2>
                <p class="application-name">{application_name}</p>
                <p class="client">Client ID: {client_id}</p>
                <h2 class="connection-title">Requested permissions</h2>
                {permissions}
                <p class="trust-note">Only approve applications you trust.
                    Registration does not mean Relay has verified this application.</p>
            </section>
        """

        if login_session:
            action_html = f"""
                <div class="status">
                    <span class="status-dot"></span>
                    Signed in to Relay
                </div>

                <h1>Approve this connection</h1>
                <p class="subtitle">
                    Review the permissions before connecting
                    this application to your workspace.
                </p>

                {connection_html}
                <p class="subtitle">Approving grants these permissions within your
                    existing Relay workspace access. Your password is not shared
                    with the application.</p>
                <form method="POST" action="/oauth/approve">
                    {hidden_fields}

                    <button class="btn primary" type="submit"
                            name="decision" value="approve">
                        Approve access
                        <span aria-hidden="true">&#8594;</span>
                    </button>

                    <button class="btn secondary" type="submit"
                            name="decision" value="deny">
                        Deny
                    </button>
                </form>
            """
        else:
            action_html = f"""
                <h1>Connect to Relay</h1>
                <p class="subtitle">
                    Sign in to your Relay account to continue.
                </p>

                {connection_html}
                <form method="POST" action="/oauth/login">
                    {hidden_fields}

                    <label for="email">Email address</label>
                    <input
                        id="email"
                        type="email"
                        name="email"
                        placeholder="you@example.com"
                        autocomplete="username"
                        required
                    >

                    <label for="password">Password</label>
                    <input
                        id="password"
                        type="password"
                        name="password"
                        placeholder="Enter your password"
                        autocomplete="current-password"
                        required
                    >

                    <button class="btn primary" type="submit">
                        Continue with Relay
                        <span aria-hidden="true">&#8594;</span>
                    </button>
                </form>
            """

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">
            <title>Connect to Relay</title>

            <link rel="stylesheet" href="/oauth/static/relay.css">
        </head>
        <body>
            <main class="container">
                <div class="brand">
                    <img class="logo" src="/oauth/static/relay-light.png"
                         alt="Relay" width="1983" height="793">
                </div>

                <section class="card" aria-label="Connect to Relay">
                    {action_html}
                </section>
                <p class="footer">Relay &mdash; Your workflows. Your control.</p>
            </main>
        </body>
        </html>
        """

        headers = {}
        if login_session:
            # Chromium checks form redirects too. Permit only the callback already
            # validated by the authorization flow, never a URL from this page's query.
            # CSP source expressions cannot contain query strings or fragments.
            callback = urlsplit(str(pending.params.redirect_uri))
            source = (
                f"{callback.scheme}://{quote(callback.netloc, safe=':[]')}"
                f"{quote(callback.path or '/', safe='/%:@-._~!$&()*+=')}"
            )
            headers["Content-Security-Policy"] = HTML_CSP.replace(
                "form-action 'self'", f"form-action 'self' {source}"
            )
        return HTMLResponse(html, headers=headers)

    return consent_page
