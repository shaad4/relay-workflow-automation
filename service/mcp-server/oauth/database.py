"""Durable OAuth state for the single-worker MCP deployment."""

import base64
import fcntl
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class OAuthDatabase:
    def __init__(self, secret=None, deployment_mode=None):
        path = os.environ.get("MCP_CLIENT_DB_PATH", ":memory:")
        production = (deployment_mode or os.environ.get("MCP_DEPLOYMENT_MODE")) == "k3s"
        if production and (path == ":memory:" or not Path(path).is_absolute()):
            raise ValueError("K3s requires an absolute persistent MCP_CLIENT_DB_PATH")
        self.lock_file = None
        self.connection = None
        secret = secret or os.environ.get("MCP_SESSION_SECRET", "")
        explicit_key = os.environ.get("MCP_CREDENTIAL_ENCRYPTION_KEY")
        if explicit_key:
            try:
                self.cipher = Fernet(explicit_key.encode())
            except (ValueError, TypeError):
                raise ValueError("MCP_CREDENTIAL_ENCRYPTION_KEY must be a Fernet key") from None
        elif len(secret) >= 32:
            # Domain separation from the browser-cookie signing key. The existing
            # Kubernetes Secret is stable; a dedicated Fernet key is also supported.
            key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"relay-mcp/oauth-credentials/v1",
            ).derive(secret.encode())
            self.cipher = Fernet(base64.urlsafe_b64encode(key))
        elif path == ":memory:" and not production:
            self.cipher = Fernet(Fernet.generate_key())
        else:
            raise ValueError("Persistent OAuth storage requires a stable MCP_SESSION_SECRET")

        try:
            if path != ":memory:":
                # Prevent a second process from independently rotating the same
                # delegated refresh credential. Recreate deployments release this lock.
                fd = os.open(path + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
                self.lock_file = os.fdopen(fd, "a")
                os.fchmod(fd, 0o600)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise RuntimeError(
                        "OAuth database already in use; run one MCP worker"
                    ) from None
                fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
                os.fchmod(fd, 0o600)
                os.close(fd)
            self.connection = sqlite3.connect(path, timeout=5, isolation_level=None)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA synchronous = FULL")
            with self.transaction():
                # Additive migration: existing client registrations remain valid.
                for statement in (
                    "CREATE TABLE IF NOT EXISTS oauth_clients "
                    "(client_id TEXT PRIMARY KEY, metadata TEXT NOT NULL)",
                    "CREATE TABLE IF NOT EXISTS oauth_settings "
                    "(name TEXT PRIMARY KEY, value TEXT NOT NULL)",
                    "CREATE TABLE IF NOT EXISTS oauth_grants ("
                    "grant_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, resource TEXT NOT NULL, "
                    "subject TEXT NOT NULL, workspace_id TEXT NOT NULL, session TEXT NOT NULL, "
                    "expires_at INTEGER NOT NULL, revoked_at INTEGER, "
                    "refresh_pending INTEGER NOT NULL DEFAULT 0)",
                    "CREATE TABLE IF NOT EXISTS oauth_tokens ("
                    "token_hash TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('access', 'refresh')), "
                    "grant_id TEXT NOT NULL REFERENCES oauth_grants(grant_id) ON DELETE CASCADE, "
                    "scopes TEXT NOT NULL, expires_at INTEGER NOT NULL, consumed_at INTEGER)",
                    "CREATE INDEX IF NOT EXISTS oauth_tokens_grant ON oauth_tokens(grant_id)",
                ):
                    self.connection.execute(statement)
                marker = self.connection.execute(
                    "SELECT value FROM oauth_settings WHERE name = 'encryption_key_check'"
                ).fetchone()
                if marker:
                    if self.decrypt(marker[0]) != {"version": 1}:
                        raise ValueError("Unsupported OAuth encryption format")
                else:
                    self.connection.execute(
                        "INSERT INTO oauth_settings VALUES ('encryption_key_check', ?)",
                        (self.encrypt({"version": 1}),),
                    )
        except Exception:
            self.close()
            raise

    @contextmanager
    def transaction(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def encrypt(self, value):
        return self.cipher.encrypt(json.dumps(value).encode()).decode()

    def decrypt(self, value):
        try:
            return json.loads(self.cipher.decrypt(value.encode()))
        except (InvalidToken, ValueError):
            raise ValueError(
                "OAuth credentials cannot be decrypted; check the stable key"
            ) from None

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self.lock_file is not None:
            self.lock_file.close()
            self.lock_file = None
