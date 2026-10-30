import base64
import hashlib
import os
import secrets
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from starlette.responses import JSONResponse
from starlette.routing import Route

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from remote_server import create_remote_app, main
from user_session import UserRelaySession

PUBLIC = "https://mcp.relay.shaad.site"
INGRESS = "10.42.1.7"


class DeploymentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "MCP_DEPLOYMENT_MODE": "k3s",
                "MCP_PUBLIC_ORIGIN": PUBLIC,
                "MCP_TRUSTED_PROXY_IPS": INGRESS,
                "MCP_SESSION_SECRET": secrets.token_urlsafe(32),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.app = create_remote_app()

    def client(self, peer=INGRESS, base_url=PUBLIC):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app, client=(peer, 4321)), base_url=base_url
        )

    async def test_ingress_metadata_host_and_forwarded_headers(self):
        async with self.client() as client:
            response = await client.get(
                "/.well-known/oauth-authorization-server",
                headers={
                    "x-forwarded-host": "evil.invalid",
                    "forwarded": "host=evil.invalid;proto=http",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["issuer"].rstrip("/"), PUBLIC)
            self.assertEqual(response.json()["authorization_endpoint"], PUBLIC + "/authorize")
            metadata = await client.get("/.well-known/oauth-protected-resource/mcp")
            self.assertEqual(metadata.json()["resource"], PUBLIC + "/mcp")
            response = await client.get(
                "/.well-known/oauth-authorization-server",
                headers={"host": "evil.invalid", "x-forwarded-host": "mcp.relay.shaad.site"},
            )
            self.assertEqual(response.status_code, 400)
        async with self.client("192.0.2.8") as client:
            response = await client.get(
                "/.well-known/oauth-authorization-server",
                headers={"x-forwarded-for": INGRESS, "x-forwarded-proto": "https"},
            )
            self.assertEqual(response.status_code, 403)

    async def test_proxy_trust_precedes_header_processing(self):
        async def probe(request):
            return JSONResponse({"scheme": request.url.scheme, "peer": request.client.host})

        self.app.router.routes.insert(0, Route("/probe", probe))
        async with self.client(base_url="http://mcp.relay.shaad.site") as client:
            response = await client.get(
                "/probe", headers={"x-forwarded-for": "198.51.100.9", "x-forwarded-proto": "https"}
            )
            self.assertEqual(response.json(), {"scheme": "https", "peer": "198.51.100.9"})
        with patch.dict(
            os.environ,
            {"MCP_DEPLOYMENT_MODE": "local", "MCP_PUBLIC_ORIGIN": "http://127.0.0.1:8001"},
        ):
            self.app = create_remote_app()
        self.app.router.routes.insert(0, Route("/probe", probe))
        async with self.client("127.0.0.1", "http://127.0.0.1:8001") as client:
            response = await client.get(
                "/probe", headers={"x-forwarded-for": "198.51.100.9", "x-forwarded-proto": "https"}
            )
            self.assertEqual(response.json(), {"scheme": "http", "peer": "127.0.0.1"})
        async with self.client(INGRESS, "http://127.0.0.1:8001") as client:
            self.assertEqual(
                (await client.get("/probe", headers={"x-forwarded-for": "127.0.0.1"})).status_code,
                403,
            )

    async def test_oauth_protection_audience_expiry_revocation_and_origin(self):
        provider = self.app.state.provider
        grant_id = secrets.token_urlsafe(32)
        provider.grants[grant_id] = {
            "session": UserRelaySession(
                "https://relay.invalid",
                secrets.token_urlsafe(32),
                secrets.token_urlsafe(32),
                user_id="demo",
                workspace_id="demo-workspace",
            ),
            "subject": "demo",
            "expires_at": time.time() + 3600,
        }
        pair = provider._issue("demo-client", ["relay:read"], grant_id)
        headers = {"Accept": "application/json, text/event-stream"}
        body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        async with self.app.router.lifespan_context(self.app):
            async with self.client() as client:
                for token in (None, secrets.token_urlsafe(32)):
                    auth = {} if token is None else {"Authorization": "Bearer " + token}
                    self.assertEqual(
                        (
                            await client.post("/mcp", headers={**headers, **auth}, json=body)
                        ).status_code,
                        401,
                    )
                headers["Authorization"] = "Bearer " + pair.access_token
                self.assertEqual(
                    (await client.post("/mcp", headers=headers, json=body)).status_code, 200
                )
                self.assertEqual(
                    (
                        await client.post(
                            "/mcp", headers={**headers, "Origin": "https://evil.invalid"}, json=body
                        )
                    ).status_code,
                    403,
                )
                record = provider.access_tokens[pair.access_token]
                record.resource = "http://127.0.0.1:8001/mcp"
                self.assertEqual(
                    (await client.post("/mcp", headers=headers, json=body)).status_code, 401
                )
                record.resource = PUBLIC + "/mcp"
                record.expires_at = int(time.time()) - 1
                self.assertEqual(
                    (await client.post("/mcp", headers=headers, json=body)).status_code, 401
                )
                pair = provider._issue("demo-client", ["relay:read"], grant_id)
                headers["Authorization"] = "Bearer " + pair.access_token
                await provider.revoke_token(provider.access_tokens[pair.access_token])
                self.assertEqual(
                    (await client.post("/mcp", headers=headers, json=body)).status_code, 401
                )

    async def test_browser_csrf_and_secure_cookie(self):
        async with self.client() as client:
            registered = await client.post(
                "/register",
                json={
                    "redirect_uris": ["http://127.0.0.1:9000/callback"],
                    "token_endpoint_auth_method": "none",
                },
            )
            self.assertEqual(registered.status_code, 201)
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(secrets.token_bytes(32)).digest())
                .decode()
                .rstrip("=")
            )
            response = await client.get(
                "/authorize",
                params={
                    "client_id": registered.json()["client_id"],
                    "redirect_uri": "http://127.0.0.1:9000/callback",
                    "response_type": "code",
                    "resource": PUBLIC + "/mcp",
                    "code_challenge_method": "S256",
                    "code_challenge": challenge,
                },
            )
            self.assertEqual(response.status_code, 302)
            page = await client.get(response.headers["location"])
            self.assertIn("secure", page.headers["set-cookie"].lower())
            for path in ("/oauth/login", "/oauth/approve"):
                for origin in (PUBLIC, "https://evil.invalid"):
                    response = await client.post(
                        path, headers={"Origin": origin}, data={"csrf_token": "invalid"}
                    )
                    self.assertEqual(response.status_code, 403)

    async def test_configuration_fails_closed(self):
        for changes in (
            {"MCP_DEPLOYMENT_MODE": "unknown"},
            {"MCP_TRUSTED_PROXY_IPS": ""},
            {"MCP_TRUSTED_PROXY_IPS": "*"},
            {"MCP_TRUSTED_PROXY_IPS": "0.0.0.0/0"},
            {"MCP_TRUSTED_PROXY_IPS": "::/0"},
            {"MCP_PUBLIC_ORIGIN": "http://mcp.relay.shaad.site"},
            {"MCP_PUBLIC_ORIGIN": PUBLIC + "/path"},
            {"MCP_PUBLIC_ORIGIN": "https://evil.invalid"},
            {"MCP_DEPLOYMENT_MODE": "local"},
        ):
            with (
                self.subTest(changes=changes),
                patch.dict(os.environ, changes),
                self.assertRaises(ValueError),
            ):
                create_remote_app()

    async def test_runner_bind_port_worker_and_proxy_settings(self):
        for port in (None, "8123"):
            with patch.dict(os.environ, {}), patch("uvicorn.run") as run:
                os.environ.pop("MCP_PORT", None)
                if port:
                    os.environ["MCP_PORT"] = port
                main()
                self.assertEqual(run.call_args.kwargs["host"], "0.0.0.0")
                self.assertEqual(run.call_args.kwargs["port"], int(port or "8001"))
                self.assertEqual(run.call_args.kwargs["workers"], 1)
                self.assertFalse(run.call_args.kwargs["proxy_headers"])
        with (
            patch.dict(os.environ, {"MCP_PUBLIC_ORIGIN": "http://127.0.0.1:8001"}),
            patch("uvicorn.run") as run,
        ):
            os.environ.pop("MCP_DEPLOYMENT_MODE", None)
            main()
            self.assertEqual(run.call_args.kwargs["host"], "127.0.0.1")
