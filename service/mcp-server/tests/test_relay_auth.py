"""Verify real login code against a simulated existing Auth Service, without credentials."""

import secrets
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oauth.relay_auth import authenticate_relay_user
from user_session import UserRelaySession


class RelayAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_login_verifies_identity_and_preserves_server_session(self):
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        paths = []

        def handler(request):
            paths.append(request.url.path)
            if request.url.path == "/auth/login":
                return httpx.Response(
                    200,
                    headers=[
                        ("set-cookie", f"relay_access_token={access}; Path=/; HttpOnly"),
                        ("set-cookie", f"relay_refresh_token={refresh}; Path=/; HttpOnly"),
                    ],
                )
            if request.headers.get("authorization") != f"Bearer {access}":
                raise AssertionError("Expected delegated authorization header")
            return httpx.Response(200, json={"id": "user-a", "workspace_id": "workspace-a"})

        factory = httpx.AsyncClient

        def client(**kwargs):
            return factory(**kwargs, transport=httpx.MockTransport(handler))

        with (
            patch.dict("os.environ", {"RELAY_API_URL": "https://relay.invalid"}),
            patch("httpx.AsyncClient", side_effect=client),
        ):
            identity = await authenticate_relay_user(
                "demo@example.invalid", secrets.token_urlsafe(32)
            )
            session = UserRelaySession(
                "https://relay.invalid", identity["access_token"], identity["refresh_token"]
            )
            self.assertEqual((await session.get_identity())["id"], identity["user_id"])
        self.assertEqual(paths, ["/auth/login", "/auth/me", "/auth/me"])

    async def test_unverified_identity_never_accepted(self):
        factory = httpx.AsyncClient
        for status, body in ((401, {}), (200, {"id": "user-a"})):

            def handler(request):
                if request.url.path == "/auth/login":
                    return httpx.Response(
                        200,
                        headers=[
                            ("set-cookie", "relay_access_token=synthetic; Path=/"),
                            ("set-cookie", "relay_refresh_token=synthetic; Path=/"),
                        ],
                    )
                return httpx.Response(status, json=body)

            def client(**kwargs):
                return factory(**kwargs, transport=httpx.MockTransport(handler))

            with (
                patch.dict("os.environ", {"RELAY_API_URL": "https://relay.invalid"}),
                patch("httpx.AsyncClient", side_effect=client),
            ):
                with self.assertRaises((httpx.HTTPStatusError, RuntimeError)):
                    await authenticate_relay_user("demo@example.invalid", secrets.token_urlsafe(32))
