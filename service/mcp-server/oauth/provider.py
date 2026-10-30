
from mcp.server.auth.provider import (
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
)
from mcp.shared.auth import OAuthClientInformationFull

from oauth.storage import AuthorizationStore


class RelayOAuthProvider(OAuthAuthorizationServerProvider):
    def __init__(self):
        self.authorization_store = AuthorizationStore()

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """
        Save the authorization request and redirect
        the user to the future login/consent page.
        """

        request_id = self.authorization_store.create(
            client_id=client.client_id,
            params=params,
        )

        return f"/oauth/consent?request_id={request_id}"
