"""Local-only OAuth demonstration; deliberately does not mount MCP tools."""

import os
import re
from urllib.parse import urlsplit

from mcp.server.auth.handlers.authorize import AuthorizationHandler
from mcp.server.auth.handlers.register import RegistrationHandler
from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator
from mcp.server.auth.routes import create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.server.transport_security import RequestBodyLimitMiddleware
from pydantic import AnyHttpUrl, AnyUrl, TypeAdapter, ValidationError
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from oauth.approval import create_approval_handler
from oauth.consent import create_consent_page
from oauth.login import create_login_handler
from oauth.provider import RelayOAuthProvider
from oauth.revocation import create_revocation_handler
from oauth.scopes import SCOPES


def create_oauth_app(store=None, *, provider=None, public_origin=None, session_secret=None):
    origin = (public_origin or os.environ.get("MCP_PUBLIC_ORIGIN", "http://127.0.0.1:8001")).rstrip(
        "/"
    )
    parsed = urlsplit(origin)
    if (
        parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.scheme not in {"http", "https"}
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Relay MCP requires a loopback-only OAuth origin")
    secret = session_secret or os.environ.get("MCP_SESSION_SECRET", "")
    if len(secret) < 32:
        raise ValueError("MCP_SESSION_SECRET must contain at least 32 random characters")
    provider = provider or RelayOAuthProvider(origin + "/mcp", store)
    options = ClientRegistrationOptions(
        enabled=True, valid_scopes=SCOPES, default_scopes=["relay:read"]
    )
    auth_handler = AuthorizationHandler(provider)
    token_handler = TokenHandler(provider, ClientAuthenticator(provider))
    registration_handler = RegistrationHandler(provider, options)

    def error(name="invalid_request"):
        return JSONResponse({"error": name}, status_code=400, headers={"Cache-Control": "no-store"})

    def duplicates(params):
        return len(params.multi_items()) != len(params)

    async def authorize(request):
        params = request.query_params if request.method == "GET" else await request.form()
        if duplicates(params):
            return error()
        client = await provider.get_client(params.get("client_id"))
        # Compare raw input before Pydantic URL normalization, including error redirects.
        if not client or params.get("redirect_uri") not in [str(u) for u in client.redirect_uris]:
            return error()
        if params.get("code_challenge_method") != "S256":
            return error()
        return await auth_handler.handle(request)

    async def token(request):
        params = await request.form()
        if duplicates(params):
            return error()
        # SDK accepts resource but does not pass it into code/refresh exchange hooks.
        # There is exactly one supported audience; omitted resource inherits the grant.
        if "resource" in params and params["resource"] != provider.resource:
            return error("invalid_target")
        if params.get("grant_type") == "authorization_code":
            if not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", str(params.get("code_verifier", ""))):
                return error("invalid_grant")
            code = provider.code_store.get(params.get("code"), params.get("client_id"))
            if code and params.get("redirect_uri") != str(code.redirect_uri):
                return error()
        return await token_handler.handle(request)

    async def register(request):
        try:
            body = await request.json()
            uris = body.get("redirect_uris", [])
            # Require canonical registration strings so exact comparison remains possible.
            if not isinstance(uris, list) or any(
                not isinstance(uri, str) or str(TypeAdapter(AnyUrl).validate_python(uri)) != uri
                for uri in uris
            ):
                return error("invalid_redirect_uri")
        except (ValueError, TypeError, AttributeError, ValidationError):
            return error("invalid_client_metadata")
        return await registration_handler.handle(request)

    routes = create_auth_routes(
        provider,
        AnyHttpUrl(origin),
        client_registration_options=options,
        revocation_options=RevocationOptions(enabled=True),
    )
    routes = [r for r in routes if r.path not in {"/authorize", "/token", "/register", "/revoke"}]
    routes += [
        Route("/authorize", authorize, methods=["GET", "POST"]),
        Route("/token", token, methods=["POST"]),
        Route("/register", register, methods=["POST"]),
        Route("/revoke", create_revocation_handler(provider), methods=["POST"]),
        Route("/oauth/consent", create_consent_page(provider.authorization_store)),
        Route(
            "/oauth/login",
            create_login_handler(provider.authorization_store, provider.login_store, origin),
            methods=["POST"],
        ),
        Route(
            "/oauth/approve",
            create_approval_handler(
                provider.authorization_store, provider.login_store, provider.code_store, origin
            ),
            methods=["POST"],
        ),
    ]
    app = Starlette(routes=routes)
    app.state.provider = provider
    app.state.authorization_store = provider.authorization_store
    app.state.login_store = provider.login_store
    app.state.code_store = provider.code_store

    async def security_headers(request, call_next):
        provider.cleanup()
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            }
        )
        return response

    app.add_middleware(BaseHTTPMiddleware, dispatch=security_headers)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        session_cookie="relay_mcp_session",
        max_age=600,
        same_site="lax",
        https_only=parsed.scheme == "https",
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[parsed.hostname])
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=65536)
    return app
