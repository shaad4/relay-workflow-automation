"""Single-process OAuth provider. HTTP validation lives in app.py and SDK handlers."""

import re
import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    RegistrationError,
    TokenError,
)
from mcp.shared.auth import OAuthToken

from oauth.codes import AuthorizationCodeStore
from oauth.login import LoginStore
from oauth.scopes import SCOPES
from oauth.storage import AuthorizationStore


class RelayOAuthProvider(OAuthAuthorizationServerProvider):
    def __init__(self, resource="http://127.0.0.1:8001/mcp", authorization_store=None):
        self.resource = resource
        self.authorization_store = authorization_store or AuthorizationStore()
        self.login_store = LoginStore()
        self.code_store = AuthorizationCodeStore()
        self.clients = {}
        self.access_tokens = {}
        self.refresh_tokens = {}
        self.grants = {}

    def cleanup(self):
        now = time.time()
        self.authorization_store.cleanup()
        self.code_store.cleanup()
        self.login_store.cleanup()
        for key, grant in list(self.grants.items()):
            if grant["expires_at"] <= now:
                self._drop_grant(key)
        for token in list(self.refresh_tokens.values()):
            if token.expires_at <= now:
                self._drop_grant(token.grant_id)
        for key, token in list(self.access_tokens.items()):
            if token.expires_at <= now:
                self.access_tokens.pop(key, None)

    def _drop_grant(self, grant_id):
        self.grants.pop(grant_id, None)
        for store in (self.access_tokens, self.refresh_tokens):
            for key, token in list(store.items()):
                if token.grant_id == grant_id:
                    store.pop(key, None)

    async def get_client(self, client_id):
        return self.clients.get(client_id)

    async def register_client(self, client_info):
        if (
            not client_info.client_id
            or client_info.client_id in self.clients
            or not client_info.redirect_uris
            or set(client_info.grant_types) - {"authorization_code", "refresh_token"}
        ):
            raise RegistrationError("invalid_client_metadata")
        for uri in client_info.redirect_uris:
            if (
                uri.fragment
                or uri.username
                or uri.password
                or (
                    uri.scheme != "https"
                    and not (
                        uri.scheme == "http" and uri.host in {"localhost", "127.0.0.1", "[::1]"}
                    )
                )
            ):
                raise RegistrationError("invalid_redirect_uri")
        self.clients[client_info.client_id] = client_info.model_copy(deep=True)

    async def authorize(self, client, params):
        self.cleanup()
        registered_scopes = (client.scope or "").split()
        if params.scopes is None:
            params.scopes = ["relay:read"] if "relay:read" in registered_scopes else []
        if not set(params.scopes).issubset(set(SCOPES) & set(registered_scopes)):
            raise AuthorizeError("invalid_scope")
        if str(params.redirect_uri) not in [str(u) for u in client.redirect_uris]:
            raise AuthorizeError("invalid_request")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", params.code_challenge):
            raise AuthorizeError("invalid_request")
        if params.resource != self.resource:
            raise AuthorizeError("invalid_target")
        request_id = self.authorization_store.create(client.client_id, params)
        return f"/oauth/consent?request_id={request_id}"

    async def load_authorization_code(self, client, authorization_code):
        self.cleanup()
        return self.code_store.get(authorization_code, client.client_id)

    async def exchange_authorization_code(self, client, authorization_code):
        # No await between consume and issuance: atomic within this single event loop.
        code = self.code_store.consume(authorization_code.code, client.client_id)
        if code is None or code.resource != self.resource:
            raise TokenError("invalid_grant")
        grant_id = secrets.token_urlsafe(32)
        self.grants[grant_id] = {
            "session": code.relay_session,
            "subject": code.subject,
            "expires_at": time.time() + 3600,
        }
        return self._issue(client.client_id, code.scopes, grant_id)

    def _issue(self, client_id, scopes, grant_id):
        grant = self.grants[grant_id]
        common = dict(
            client_id=client_id,
            scopes=scopes,
            resource=self.resource,
            subject=grant["subject"],
            grant_id=grant_id,
        )
        access = DelegatedAccessToken(
            token=secrets.token_urlsafe(32), expires_at=int(time.time()) + 300, **common
        )
        refresh = DelegatedRefreshToken(
            token=secrets.token_urlsafe(32), expires_at=int(grant["expires_at"]), **common
        )
        self.access_tokens[access.token] = access
        self.refresh_tokens[refresh.token] = refresh
        return OAuthToken(
            access_token=access.token,
            token_type="Bearer",
            expires_in=300,
            refresh_token=refresh.token,
            scope=" ".join(scopes),
        )

    async def load_access_token(self, token):
        self.cleanup()
        access = self.access_tokens.get(token)
        if access and access.resource == self.resource and access.grant_id in self.grants:
            return access
        return None

    async def load_refresh_token(self, client, refresh_token):
        self.cleanup()
        token = self.refresh_tokens.get(refresh_token)
        if token and token.client_id == client.client_id and token.resource == self.resource:
            return token
        return None

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        self.cleanup()
        token = self.refresh_tokens.get(refresh_token.token)
        if token is None or token.client_id != client.client_id:
            raise TokenError("invalid_grant")
        if not set(scopes).issubset(token.scopes):
            raise TokenError("invalid_scope")
        grant = self.grants[token.grant_id]
        self._drop_grant(token.grant_id)
        self.grants[token.grant_id] = grant
        return self._issue(client.client_id, scopes, token.grant_id)

    async def revoke_token(self, token):
        self._drop_grant(token.grant_id)


class DelegatedAccessToken(AccessToken):
    grant_id: str


class DelegatedRefreshToken(RefreshToken):
    grant_id: str
