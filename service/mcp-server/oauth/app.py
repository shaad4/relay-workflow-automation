"""OAuth routes shared by the local and explicitly configured K3s applications."""

import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from mcp.server.auth.handlers.authorize import AuthorizationHandler
from mcp.server.auth.handlers.metadata import MetadataHandler
from mcp.server.auth.handlers.register import RegistrationHandler
from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator
from mcp.server.auth.routes import build_metadata, cors_middleware, create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.server.transport_security import RequestBodyLimitMiddleware
from pydantic import AnyHttpUrl, AnyUrl, TypeAdapter, ValidationError
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from oauth.approval import create_approval_handler
from oauth.consent import HTML_CSP, create_consent_page
from oauth.login import create_login_handler
from oauth.provider import RelayOAuthProvider
from oauth.revocation import create_revocation_handler
from oauth.scopes import SCOPES


def create_oauth_app(
    store=None, *, provider=None, public_origin=None, session_secret=None, deployment_mode="local"
):
    origin = (public_origin or os.environ.get("MCP_PUBLIC_ORIGIN", "http://127.0.0.1:8001")).rstrip(
        "/"
    )
    parsed = urlsplit(origin)
    if deployment_mode not in {"local", "k3s"}:
        raise ValueError("MCP_DEPLOYMENT_MODE must be local or k3s")
    if deployment_mode == "k3s" and origin != "https://mcp.relay.shaad.site":
        raise ValueError("K3s requires MCP_PUBLIC_ORIGIN=https://mcp.relay.shaad.site")
    if deployment_mode == "local" and (
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

    def error(name="invalid_request", description="Invalid OAuth request"):
        return JSONResponse(
            {"error": name, "error_description": description},
            status_code=400,
            headers={"Cache-Control": "no-store"},
        )

    def duplicates(params):
        return len(params.multi_items()) != len(params)

    async def authorize(request):
        params = request.query_params if request.method == "GET" else await request.form()
        if duplicates(params):
            return error(description="Duplicate authorization parameters are not allowed")
        if any(not isinstance(value, str) for value in params.values()):
            return error(description="Authorization parameters must be strings")
        if not params.get("client_id"):
            return error(description="client_id is required")
        client = await provider.get_client(params["client_id"])
        if client is None:
            return error(
                description="Unknown client registration; register again after a server restart"
            )
        # Compare decoded query/form values exactly, before SDK URL normalization.
        # Never send an error to an unregistered redirect or echo submitted values.
        if params.get("redirect_uri") not in [str(u) for u in client.redirect_uris]:
            return error(description="redirect_uri must exactly match a registered URI")
        if params.get("code_challenge_method") != "S256":
            return error(description="code_challenge_method must be S256")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", params.get("code_challenge", "")):
            return error(description="A valid S256 code_challenge is required")
        if params.get("response_type") != "code":
            return error("unsupported_response_type", "response_type must be code")
        if params.get("resource") != provider.resource:
            return error("invalid_target", "resource must exactly match this MCP endpoint")
        if "scope" in params:
            scopes = set(params["scope"].split(" "))
            if not scopes.issubset(set(SCOPES) & set((client.scope or "").split())):
                return error("invalid_scope", "Requested scopes must be supported and registered")
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
                return error(
                    "invalid_redirect_uri", "Register canonical absolute redirect URI strings"
                )
        except (ValueError, TypeError, AttributeError, ValidationError):
            return error("invalid_client_metadata")
        return await registration_handler.handle(request)

    routes = create_auth_routes(
        provider,
        AnyHttpUrl(origin),
        client_registration_options=options,
        revocation_options=RevocationOptions(enabled=True),
    )
    # SDK 2.3.0 supports public clients but omits "none" from its metadata.
    metadata = build_metadata(AnyHttpUrl(origin), None, options, RevocationOptions(enabled=True))
    metadata.token_endpoint_auth_methods_supported = [
        "none",
        "client_secret_post",
        "client_secret_basic",
    ]
    metadata.revocation_endpoint_auth_methods_supported = (
        metadata.token_endpoint_auth_methods_supported
    )
    replaced_paths = {
        "/authorize",
        "/token",
        "/register",
        "/revoke",
        "/.well-known/oauth-authorization-server",
    }
    routes = [r for r in routes if r.path not in replaced_paths]
    routes.append(
        Route(
            "/.well-known/oauth-authorization-server",
            endpoint=cors_middleware(MetadataHandler(metadata).handle, ["GET", "OPTIONS"]),
            methods=["GET", "OPTIONS"],
        )
    )

    async def stylesheet(request):
        return FileResponse(Path(__file__).parent / "static" / "relay.css", media_type="text/css")

    async def logo(request):
        return FileResponse(
            Path(__file__).parent / "static" / "relay-light.png", media_type="image/png"
        )

    routes += [
        Route("/oauth/static/relay-light.png", logo, methods=["GET", "HEAD"]),
        Route("/oauth/static/relay.css", stylesheet, methods=["GET", "HEAD"]),
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
        csp = "default-src 'none'; frame-ancestors 'none'"
        if request.url.path.startswith("/oauth/") and response.headers.get(
            "content-type", ""
        ).startswith("text/html"):
            csp = response.headers.get("Content-Security-Policy", HTML_CSP)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                # Keep the same-origin Referer fallback usable on form submissions,
                # while suppressing referrers on external OAuth callbacks.
                "Referrer-Policy": "same-origin",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": csp,
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
