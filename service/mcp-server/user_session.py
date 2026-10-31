"""Server-side Relay credentials; never serialize this object to a client."""

import httpx
from mcp.server.mcpserver.exceptions import ToolError


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

    async def get_identity(self) -> dict:
        # Short-lived clients avoid retaining open transports in expiring memory stores.
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=15.0, follow_redirects=False
        ) as client:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def close(self):
        pass  # No persistent transport.


class RelayAccessError(ToolError):
    """Safe public error: never include upstream responses or credentials."""


class DelegatedRequestSession:
    """One tool invocation's HTTP client; authorization is checked before every call."""

    def __init__(self, session, client, check_grant):
        self.session = session
        self.client = client
        self.check_grant = check_grant

    async def verify_identity(self):
        await self.check_grant()
        try:
            response = await self.client.get("/auth/me")
            response.raise_for_status()
            identity = response.json()
            if (
                not self.session.user_id
                or not self.session.workspace_id
                or str(identity.get("id")) != self.session.user_id
                or str(identity.get("workspace_id")) != self.session.workspace_id
            ):
                raise RelayAccessError("Relay identity changed; authorize again")
        except (httpx.HTTPError, ValueError, AttributeError):
            raise RelayAccessError(
                "Relay session unavailable or expired; authorize again"
            ) from None
        await self.check_grant()

    async def get(self, path, **kwargs):
        return await self.request("GET", path, **kwargs)

    async def request(self, method, path, **kwargs):
        await self.verify_identity()
        try:
            # No retries, including uncertain mutations. Never follow redirects.
            response = await self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPError:
            raise RelayAccessError(
                "Relay request failed or access denied; mutation outcome may be unknown"
            ) from None
