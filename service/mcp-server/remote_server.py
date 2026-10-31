"""OAuth-protected Streamable HTTP in local or explicit K3s deployment mode."""

import os
from contextlib import asynccontextmanager
from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

import httpx
from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import ProviderTokenVerifier
from mcp.server.auth.routes import create_protected_resource_routes
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError
from mcp.types import Icon
from oauth.app import create_oauth_app
from oauth.scopes import SCOPES, TOOL_SCOPES, InsufficientScopeError
from pydantic import AnyHttpUrl
from relay_client import RelayClient
from starlette.responses import PlainTextResponse
from starlette.routing import Mount
from tools import register_tools
from user_session import DelegatedRequestSession, RelayAccessError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


class LoopbackOnlyMiddleware:
    """Defense in depth; the supported runner also binds only to 127.0.0.1."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            try:
                local = ip_address(scope.get("client", ("", 0))[0]).is_loopback
            except (ValueError, TypeError):
                local = False
            if not local:
                await PlainTextResponse("Loopback access only", status_code=403)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


def trusted_ingress_networks():
    """Require explicit ingress peer addresses; never inherit FORWARDED_ALLOW_IPS."""
    entries = os.environ.get("MCP_TRUSTED_PROXY_IPS", "").split(",")
    try:
        networks = [ip_network(entry.strip()) for entry in entries]
    except ValueError:
        raise ValueError("MCP_TRUSTED_PROXY_IPS requires ingress IP addresses or CIDRs") from None
    if any(network.prefixlen == 0 for network in networks):
        raise ValueError("MCP_TRUSTED_PROXY_IPS must not trust all addresses")
    return networks


class TrustedIngressMiddleware:
    """Check the actual socket peer before interpreting any forwarded headers."""

    def __init__(self, app, networks):
        self.networks = networks
        self.app = ProxyHeadersMiddleware(app, trusted_hosts=[str(n) for n in networks])

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            try:
                peer = ip_address(scope.get("client", ("", 0))[0])
                trusted = any(peer in network for network in self.networks)
            except (ValueError, TypeError):
                trusted = False
            if not trusted:
                await PlainTextResponse("Trusted ingress required", status_code=403)(
                    scope, receive, send
                )
                return
        await self.app(scope, receive, send)


class RemoteRelayClient(RelayClient):
    def __init__(self, session, secrets):
        super().__init__(session)
        self.secrets = [value for value in secrets if value]

    def sanitize_result(self, result):
        if isinstance(result, dict):
            credential_fields = {
                "access_token",
                "refresh_token",
                "password",
                "authorization",
                "cookie",
                "set-cookie",
                "client_secret",
                "relay_access_token",
                "relay_refresh_token",
            }
            sanitized = {}
            for key, value in result.items():
                safe_key = self.sanitize_result(key)
                if str(key).lower() in credential_fields:
                    sanitized[safe_key] = "[redacted]"
                else:
                    sanitized[safe_key] = self.sanitize_result(value)
            return sanitized

        if isinstance(result, list):
            return [self.sanitize_result(value) for value in result]

        if isinstance(result, str):
            for value in self.secrets:
                result = result.replace(value, "[redacted]")

        return result


def remote_client_context(provider, *, relay_transport=None):
    @asynccontextmanager
    async def context(tool_name):
        token = get_access_token()
        if token is None:
            raise RelayAccessError("OAuth authentication required")

        current = await provider.load_access_token(token.token)
        if current is None:
            raise RelayAccessError("OAuth authorization expired or revoked")

        scope = TOOL_SCOPES[tool_name]
        if scope and scope not in current.scopes:
            raise InsufficientScopeError(scope)

        grant = provider.grants.get(current.grant_id)
        if grant is None:
            raise RelayAccessError("OAuth authorization expired or revoked")

        session = grant["session"]
        if session.user_id != current.subject:
            raise RelayAccessError("Relay identity mismatch; authorize again")

        async def check_grant():
            active = await provider.load_access_token(token.token)
            if active is None or active.grant_id != current.grant_id:
                raise RelayAccessError("OAuth authorization expired or revoked")

        # A new client for each tool invocation, with only this user's bearer credential.
        async with httpx.AsyncClient(
            base_url=session.base_url,
            timeout=15.0,
            follow_redirects=False,
            transport=relay_transport,
            headers={"Authorization": f"Bearer {session.access_token}"},
        ) as http:
            request_session = DelegatedRequestSession(session, http, check_grant)
            credentials = [token.token, session.access_token, session.refresh_token]
            credentials += [
                t.token for t in provider.refresh_tokens.values() if t.grant_id == current.grant_id
            ]
            client = RemoteRelayClient(request_session, credentials)
            try:
                if tool_name != "relay_hello":
                    await request_session.verify_identity()
                yield client
            except RelayAccessError:
                raise
            except Exception:
                # SDK tool errors and complete-workflow failures must not reveal upstream bodies.
                raise RelayAccessError(
                    "Relay operation failed; mutation outcome may be unknown"
                ) from None

    return context


async def reject_identity_arguments(ctx, call_next):
    # Runs on raw arguments before the SDK discards unknown schema fields.
    if ctx.method == "tools/call":
        arguments = (ctx.params or {}).get("arguments")
        if isinstance(arguments, dict) and {"user_id", "workspace_id"} & arguments.keys():
            raise MCPError(-32602, "User and workspace identity must come from OAuth authorization")
    return await call_next(ctx)


def create_remote_app(
    *, provider=None, public_origin=None, session_secret=None, relay_transport=None
):
    mode = os.environ.get("MCP_DEPLOYMENT_MODE", "local")
    if mode not in {"local", "k3s"}:
        raise ValueError("MCP_DEPLOYMENT_MODE must be local or k3s")
    networks = trusted_ingress_networks() if mode == "k3s" else None
    origin = (public_origin or os.environ.get("MCP_PUBLIC_ORIGIN", "http://127.0.0.1:8001")).rstrip(
        "/"
    )
    app = create_oauth_app(
        provider=provider, public_origin=origin, session_secret=session_secret, deployment_mode=mode
    )
    provider = app.state.provider
    if provider.resource != origin + "/mcp":
        raise ValueError("OAuth resource must exactly match the MCP endpoint")
    mcp = MCPServer(
        "Relay MCP Server",
        icons=[
            Icon(
                src=origin + "/oauth/static/relay-icon-black.png",
                mime_type="image/png",
                sizes=["1308x1202"],
            )
        ],
        log_level="ERROR",
        token_verifier=ProviderTokenVerifier(provider),
        middleware=[reject_identity_arguments],
        auth=AuthSettings(
            issuer_url=origin,
            resource_server_url=provider.resource,
            validate_token_resource=True,
            required_scopes=[],
        ),
    )
    register_tools(
        mcp,
        remote_client_context(provider, relay_transport=relay_transport),
        oauth_resource=provider.resource,
    )
    mcp_app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        host="127.0.0.1",
        transport_security=TransportSecuritySettings(
            allowed_hosts=[urlsplit(origin).netloc],
            allowed_origins=[origin],
        ),
    )
    # Scope requirements differ by tool, so discovery advertises all supported scopes
    # without requiring every scope at the transport boundary.
    app.router.routes.extend(
        create_protected_resource_routes(
            resource_url=AnyHttpUrl(provider.resource),
            authorization_servers=[AnyHttpUrl(origin)],
            scopes_supported=SCOPES,
        )
    )
    app.router.routes.append(Mount("/", app=mcp_app))

    @asynccontextmanager
    async def lifespan(application):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app.router.lifespan_context = lifespan
    if mode == "local":
        app.add_middleware(LoopbackOnlyMiddleware)
    else:
        app.add_middleware(TrustedIngressMiddleware, networks=networks)
    app.state.mcp = mcp
    return app


def main():
    import uvicorn

    origin = os.environ.get("MCP_PUBLIC_ORIGIN", "http://127.0.0.1:8001").rstrip("/")
    mode = os.environ.get("MCP_DEPLOYMENT_MODE", "local")
    app = create_remote_app()
    if mode == "local" and urlsplit(origin).scheme != "http":
        raise ValueError("The local runner supports HTTP loopback only")
    port = (
        int(os.environ.get("MCP_PORT", "8001"))
        if mode == "k3s"
        else (urlsplit(origin).port or 8001)
    )
    if not 1 <= port <= 65535:
        raise ValueError("MCP_PORT must be between 1 and 65535")
    uvicorn.run(
        app,
        host="0.0.0.0" if mode == "k3s" else "127.0.0.1",
        port=port,
        workers=1,
        proxy_headers=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()
