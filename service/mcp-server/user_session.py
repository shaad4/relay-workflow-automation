"""Server-side Relay credentials; never serialize this object to a client."""

import math
import time
from urllib.parse import urlsplit

import httpx
import jwt
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, TextContent
from oauth.audit import audit_event


def token_expiry(token, expected_type=None):
    """Read trusted upstream token metadata for scheduling, never for authentication."""
    try:
        claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        if expected_type and claims.get("type") != expected_type:
            return None
        expiry = claims.get("exp")
        if isinstance(expiry, bool) or not isinstance(expiry, (float, int)):
            return None
        return expiry if math.isfinite(expiry) and 0 < expiry < 2**63 else None
    except (jwt.PyJWTError, ValueError, TypeError, OverflowError):
        return None


class UserRelaySession:
    def __init__(
        self,
        base_url: str,
        access_token: str,
        refresh_token: str,
        *,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.refresh_token = refresh_token


class RelayAccessError(ToolError):
    """Safe public error: never include upstream responses or credentials."""


class ReauthorizationRequired(RelayAccessError):
    def as_tool_result(self, resource):
        metadata_url = resource.removesuffix("/mcp") + "/.well-known/oauth-protected-resource/mcp"
        return CallToolResult(
            is_error=True,
            content=[TextContent(type="text", text=str(self))],
            meta={
                "mcp/www_authenticate": [
                    f'Bearer resource_metadata="{metadata_url}", error="invalid_token", '
                    'error_description="Reconnect Relay to renew authorization"'
                ]
            },
        )


class DelegatedRequestSession:
    """One tool invocation's HTTP client; authorization is checked before every call."""

    def __init__(self, session, client, check_grant, *, provider, grant_id, credentials):
        self.session = session
        self.client = client
        self.check_grant = check_grant
        self.provider = provider
        self.grant_id = grant_id
        self.credentials = credentials

    def remember_credentials(self):
        self.credentials.extend([self.session.access_token, self.session.refresh_token])

    def authorization(self):
        return {"Authorization": f"Bearer {self.session.access_token}"}

    async def _refresh(self):
        await self.check_grant()
        self.provider.begin_session_refresh(self.grant_id)
        origin = urlsplit(self.session.base_url)
        try:
            response = await self.client.post(
                "/auth/refresh",
                headers={
                    "Cookie": f"relay_refresh_token={self.session.refresh_token}",
                    "Origin": f"{origin.scheme}://{origin.netloc}",
                },
            )
        except httpx.HTTPError:
            audit_event("delegated_refresh_ambiguous", grant_id=self.grant_id, reason="network")
            raise RelayAccessError("Relay credential refresh is unavailable; try again") from None
        if response.status_code in {400, 401, 403}:
            self.provider.revoke_grant(self.grant_id)
            audit_event(
                "delegated_refresh_rejected", grant_id=self.grant_id, status=response.status_code
            )
            raise ReauthorizationRequired(
                "Relay authorization expired or was revoked; reconnect Relay"
            )
        try:
            response.raise_for_status()
            access = response.cookies.get("relay_access_token")
            refresh = response.cookies.get("relay_refresh_token")
            if not access or not refresh:
                raise ValueError("Missing credentials")
            self.credentials.extend([access, refresh])
            expiry = token_expiry(access, "access")
            if expiry is None or expiry <= time.time():
                raise ValueError("Invalid credential lifetime")
        except (httpx.HTTPError, httpx.CookieConflict, ValueError):
            audit_event(
                "delegated_refresh_ambiguous", grant_id=self.grant_id, status=response.status_code
            )
            raise RelayAccessError(
                "Relay credential refresh returned an invalid response; try again"
            ) from None
        finally:
            # Upstream cookies have /auth paths which may differ behind the gateway.
            # Send the refresh cookie explicitly and use only Bearer auth for API calls.
            self.client.cookies.clear()
        self.session.access_token = access
        self.session.refresh_token = refresh
        # Commit the rotated credentials before another network operation. A later
        # /auth/me outage must not discard a successfully rotated refresh token.
        self.provider.save_session(self.grant_id, self.session)
        audit_event("delegated_refresh_succeeded", grant_id=self.grant_id)

    async def verify_identity(self):
        async with self.provider.session_lock(self.grant_id):
            await self.check_grant()
            # Another tool may already have refreshed while this request waited.
            self.session = self.provider.load_session(self.grant_id)
            self.remember_credentials()
            expiry = token_expiry(self.session.access_token, "access")
            refreshed = expiry is None or expiry <= time.time() + 60
            if refreshed:
                await self._refresh()
            try:
                response = await self.client.get("/auth/me", headers=self.authorization())
                if response.status_code == 401 and not refreshed:
                    await self._refresh()
                    response = await self.client.get("/auth/me", headers=self.authorization())
                if response.status_code == 401:
                    self.provider.revoke_grant(self.grant_id)
                    audit_event("delegated_identity_rejected", grant_id=self.grant_id, status=401)
                    raise ReauthorizationRequired(
                        "Relay authorization is no longer valid; reconnect Relay"
                    )
                if response.status_code == 403:
                    audit_event("delegated_identity_rejected", grant_id=self.grant_id, status=403)
                    raise RelayAccessError("Relay access denied; check your account permissions")
                response.raise_for_status()
                identity = response.json()
                if not isinstance(identity, dict):
                    raise ValueError("Invalid identity response")
                if (
                    not self.session.user_id
                    or not self.session.workspace_id
                    or str(identity.get("id")) != self.session.user_id
                    or str(identity.get("workspace_id")) != self.session.workspace_id
                ):
                    self.provider.revoke_grant(self.grant_id)
                    audit_event("delegated_identity_changed", grant_id=self.grant_id)
                    raise ReauthorizationRequired("Relay identity changed; reconnect Relay")
            except httpx.HTTPError as error:
                response = getattr(error, "response", None)
                audit_event(
                    "delegated_identity_unavailable",
                    grant_id=self.grant_id,
                    reason=type(error).__name__,
                    status=response.status_code if response is not None else None,
                )
                raise RelayAccessError("Relay is temporarily unavailable; try again") from None
            except ValueError:
                audit_event(
                    "delegated_identity_unavailable",
                    grant_id=self.grant_id,
                    reason="invalid_response",
                )
                raise RelayAccessError(
                    "Relay returned an invalid identity response; try again"
                ) from None
            await self.check_grant()

    async def get(self, path, **kwargs):
        return await self.request("GET", path, **kwargs)

    async def request(self, method, path, **kwargs):
        await self.verify_identity()
        try:
            # No retries, including uncertain mutations. Never follow redirects.
            headers = {**kwargs.pop("headers", {}), **self.authorization()}
            response = await self.client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError:
            raise RelayAccessError(
                "Relay request failed or access denied; mutation outcome may be unknown"
            ) from None
