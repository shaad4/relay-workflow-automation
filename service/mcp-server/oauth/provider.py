"""Persistent OAuth provider. HTTP validation lives in app.py and SDK handlers."""

import asyncio
import json
import os
import re
import secrets
import sqlite3
import time
from weakref import WeakValueDictionary

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizeError,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    RegistrationError,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from user_session import ReauthorizationRequired, UserRelaySession, token_expiry

from oauth.audit import audit_event
from oauth.codes import AuthorizationCodeStore
from oauth.database import OAuthDatabase, token_hash
from oauth.login import LoginStore
from oauth.scopes import SCOPES
from oauth.storage import AuthorizationStore


class RelayOAuthProvider(OAuthAuthorizationServerProvider):
    def __init__(
        self,
        resource="http://127.0.0.1:8001/mcp",
        authorization_store=None,
        *,
        secret=None,
        deployment_mode=None,
    ):
        self.resource = resource
        self.authorization_store = authorization_store or AuthorizationStore()
        self.login_store = LoginStore()
        self.code_store = AuthorizationCodeStore()
        try:
            self.grant_ttl = int(os.environ.get("MCP_GRANT_TTL_SECONDS", "604800"))
        except ValueError:
            raise ValueError("MCP_GRANT_TTL_SECONDS must be a positive integer") from None
        if self.grant_ttl <= 0:
            raise ValueError("MCP_GRANT_TTL_SECONDS must be a positive integer")
        self.database = OAuthDatabase(secret, deployment_mode)
        self.client_db = self.database.connection
        self._session_locks = WeakValueDictionary()
        self._next_cleanup = 0

    def close(self):
        self.database.close()

    def session_lock(self, grant_id):
        lock = self._session_locks.get(grant_id)
        if lock is None:
            lock = asyncio.Lock()
            self._session_locks[grant_id] = lock
        return lock

    def cleanup(self):
        now = time.time()
        self.authorization_store.cleanup()
        self.code_store.cleanup()
        self.login_store.cleanup()
        if now >= self._next_cleanup:
            with self.database.transaction():
                self.client_db.execute("DELETE FROM oauth_grants WHERE expires_at <= ?", (now,))
                self.client_db.execute(
                    "DELETE FROM oauth_tokens WHERE kind = 'access' AND expires_at <= ?", (now,)
                )
            self._next_cleanup = now + 60

    def _grant(self, grant_id):
        return self.client_db.execute(
            "SELECT * FROM oauth_grants WHERE grant_id = ? AND resource = ? "
            "AND revoked_at IS NULL AND expires_at > ?",
            (grant_id, self.resource, time.time()),
        ).fetchone()

    def revoke_grant(self, grant_id):
        self.client_db.execute(
            "UPDATE oauth_grants SET revoked_at = ? WHERE grant_id = ? AND revoked_at IS NULL",
            (int(time.time()), grant_id),
        )

    def load_session(self, grant_id):
        grant = self._grant(grant_id)
        if grant is None:
            raise ReauthorizationRequired("OAuth authorization expired or revoked")
        if grant["refresh_pending"]:
            # Never replay a delegated refresh after a crash/ambiguous response:
            # the auth service may already have consumed it and rotated its token.
            self.revoke_grant(grant_id)
            audit_event("delegated_refresh_interrupted", grant_id=grant_id)
            raise ReauthorizationRequired(
                "Relay credential refresh was interrupted; reconnect Relay"
            )
        session = UserRelaySession(**self.database.decrypt(grant["session"]))
        if session.user_id != grant["subject"] or session.workspace_id != grant["workspace_id"]:
            self.revoke_grant(grant_id)
            raise ReauthorizationRequired("Relay identity changed; reconnect Relay")
        return session

    def begin_session_refresh(self, grant_id):
        updated = self.client_db.execute(
            "UPDATE oauth_grants SET refresh_pending = 1 WHERE grant_id = ? "
            "AND revoked_at IS NULL AND expires_at > ? AND refresh_pending = 0",
            (grant_id, time.time()),
        )
        if updated.rowcount != 1:
            raise ReauthorizationRequired("OAuth authorization expired or revoked")

    def save_session(self, grant_id, session):
        expiry = token_expiry(session.refresh_token, "refresh")
        if expiry is None or expiry <= time.time():
            self.revoke_grant(grant_id)
            raise ReauthorizationRequired("Relay refresh credential is invalid; reconnect Relay")
        updated = self.client_db.execute(
            "UPDATE oauth_grants SET session = ?, refresh_pending = 0, "
            "expires_at = MIN(expires_at, ?) WHERE grant_id = ? AND subject = ? "
            "AND workspace_id = ? AND revoked_at IS NULL AND expires_at > ?",
            (
                self.database.encrypt(vars(session)),
                int(expiry),
                grant_id,
                session.user_id,
                session.workspace_id,
                time.time(),
            ),
        )
        if updated.rowcount != 1:
            raise ReauthorizationRequired("OAuth authorization expired or revoked")

    async def get_client(self, client_id):
        row = self.client_db.execute(
            "SELECT metadata FROM oauth_clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        return OAuthClientInformationFull.model_validate_json(row[0]) if row else None

    async def register_client(self, client_info):
        if (
            not client_info.client_id
            or await self.get_client(client_info.client_id) is not None
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
        try:
            with self.client_db:
                self.client_db.execute(
                    "INSERT INTO oauth_clients (client_id, metadata) VALUES (?, ?)",
                    (client_info.client_id, client_info.model_dump_json()),
                )
        except sqlite3.IntegrityError:
            raise RegistrationError("invalid_client_metadata") from None

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
        session = code.relay_session
        expiry = token_expiry(session.refresh_token, "refresh")
        now = int(time.time())
        if (
            expiry is None
            or expiry <= now
            or not session.user_id
            or not session.workspace_id
            or session.user_id != code.subject
        ):
            raise TokenError("invalid_grant")
        grant_id = secrets.token_urlsafe(32)
        with self.database.transaction():
            self.client_db.execute(
                "INSERT INTO oauth_grants "
                "(grant_id, client_id, resource, subject, workspace_id, session, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    grant_id,
                    client.client_id,
                    self.resource,
                    code.subject,
                    session.workspace_id,
                    self.database.encrypt(vars(session)),
                    min(now + self.grant_ttl, int(expiry)),
                ),
            )
            tokens = self._issue(client.client_id, code.scopes, grant_id)
        audit_event("grant_created", client_id=client.client_id, grant_id=grant_id)
        return tokens

    def _issue(self, client_id, scopes, grant_id):
        grant = self._grant(grant_id)
        if grant is None:
            raise TokenError("invalid_grant")
        now = int(time.time())
        common = dict(
            client_id=client_id,
            scopes=scopes,
            resource=self.resource,
            subject=grant["subject"],
            grant_id=grant_id,
        )
        access = DelegatedAccessToken(
            token=secrets.token_urlsafe(32),
            expires_at=min(now + 300, grant["expires_at"]),
            **common,
        )
        refresh = DelegatedRefreshToken(
            token=secrets.token_urlsafe(32), expires_at=int(grant["expires_at"]), **common
        )
        for kind, token in (("access", access), ("refresh", refresh)):
            self.client_db.execute(
                "INSERT INTO oauth_tokens (token_hash, kind, grant_id, scopes, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (token_hash(token.token), kind, grant_id, json.dumps(scopes), token.expires_at),
            )
        return OAuthToken(
            access_token=access.token,
            token_type="Bearer",
            expires_in=access.expires_at - now,
            refresh_token=refresh.token,
            scope=" ".join(scopes),
        )

    async def load_access_token(self, token):
        self.cleanup()
        row = self._token(token, "access")
        return self._token_model(token, row, DelegatedAccessToken) if row else None

    def _token(self, token, kind):
        return self.client_db.execute(
            "SELECT t.*, g.client_id, g.resource, g.subject FROM oauth_tokens t "
            "JOIN oauth_grants g ON g.grant_id = t.grant_id "
            "WHERE t.token_hash = ? AND t.kind = ? AND g.resource = ? "
            "AND t.expires_at > ? AND g.expires_at > ? AND g.revoked_at IS NULL",
            (token_hash(token), kind, self.resource, time.time(), time.time()),
        ).fetchone()

    @staticmethod
    def _token_model(raw, row, model):
        return model(
            token=raw,
            client_id=row["client_id"],
            resource=row["resource"],
            subject=row["subject"],
            scopes=json.loads(row["scopes"]),
            expires_at=row["expires_at"],
            grant_id=row["grant_id"],
        )

    async def load_refresh_token(self, client, refresh_token):
        self.cleanup()
        row = self._token(refresh_token, "refresh")
        if row and row["client_id"] == client.client_id:
            if row["consumed_at"] is not None:
                self.revoke_grant(row["grant_id"])
                audit_event(
                    "refresh_reuse_rejected", client_id=client.client_id, grant_id=row["grant_id"]
                )
                return None
            return self._token_model(refresh_token, row, DelegatedRefreshToken)
        return None

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        reused = False
        with self.database.transaction():
            row = self._token(refresh_token.token, "refresh")
            if row is None or row["client_id"] != client.client_id:
                raise TokenError("invalid_grant")
            if row["consumed_at"] is not None:
                self.revoke_grant(row["grant_id"])
                reused = True
            else:
                if not set(scopes).issubset(json.loads(row["scopes"])):
                    raise TokenError("invalid_scope")
                self.client_db.execute(
                    "UPDATE oauth_tokens SET consumed_at = ? WHERE token_hash = ?",
                    (int(time.time()), token_hash(refresh_token.token)),
                )
                tokens = self._issue(client.client_id, scopes, row["grant_id"])
        if reused:
            # Raise after COMMIT so family revocation is not rolled back.
            audit_event(
                "refresh_reuse_rejected", client_id=client.client_id, grant_id=row["grant_id"]
            )
            raise TokenError("invalid_grant")
        audit_event("refresh_rotated", client_id=client.client_id, grant_id=row["grant_id"])
        return tokens

    async def revoke_token(self, token):
        self.revoke_grant(token.grant_id)
        audit_event("grant_revoked", client_id=token.client_id, grant_id=token.grant_id)


class DelegatedAccessToken(AccessToken):
    grant_id: str


class DelegatedRefreshToken(RefreshToken):
    grant_id: str
