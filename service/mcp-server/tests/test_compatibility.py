"""Browser + OAuth + SDK MCP requests through the combined K3s ASGI application."""

import asyncio
import base64
import hashlib
import json
import os
import secrets
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from remote_server import create_remote_app

PUBLIC = "https://mcp.relay.shaad.site"
CALLBACK = "https://chatgpt.com/connector/oauth/callback"


class Fields(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.values = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("type") == "hidden":
            self.values[attrs["name"]] = attrs["value"]


class CompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "MCP_DEPLOYMENT_MODE": "k3s",
                "MCP_PUBLIC_ORIGIN": PUBLIC,
                "MCP_TRUSTED_PROXY_IPS": "10.42.1.7",
                "RELAY_API_URL": "https://relay.invalid/api/relay",
                "MCP_SESSION_SECRET": secrets.token_urlsafe(32),
            },
        )
        self.env.start()
        self.identities = {}
        self.relay_calls = []
        self.transport = httpx.MockTransport(self.relay)
        self.app = create_remote_app(relay_transport=self.transport)
        self.http = httpx.AsyncClient(
            base_url=PUBLIC, transport=httpx.ASGITransport(app=self.app, client=("10.42.1.7", 4321))
        )
        original_client = httpx.AsyncClient

        def relay_client(**kwargs):
            kwargs.setdefault("transport", self.transport)
            return original_client(**kwargs)

        self.mock = patch("httpx.AsyncClient", side_effect=relay_client)
        self.mock.start()
        self.ready, self.stop = asyncio.Event(), asyncio.Event()

        async def lifespan():
            async with self.app.router.lifespan_context(self.app):
                self.ready.set()
                await self.stop.wait()

        self.task = asyncio.create_task(lifespan())
        await asyncio.wait_for(self.ready.wait(), 5)
        self.verifier = secrets.token_urlsafe(48)
        self.challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )

    async def asyncTearDown(self):
        await self.http.aclose()
        self.stop.set()
        await self.task
        self.mock.stop()
        self.env.stop()

    def relay(self, request):
        path = request.url.path.removeprefix("/api/relay")
        if path == "/auth/login":
            user = json.loads(request.content)["email"].split("@")[0]
            access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self.identities[access] = {"id": user, "workspace_id": "workspace-" + user}
            return httpx.Response(
                200,
                headers=[
                    ("set-cookie", f"relay_access_token={access}; Path=/; Secure; HttpOnly"),
                    ("set-cookie", f"relay_refresh_token={refresh}; Path=/; Secure; HttpOnly"),
                ],
            )
        identity = self.identities.get(
            request.headers.get("authorization", "").removeprefix("Bearer ")
        )
        if identity is None:
            return httpx.Response(401)
        self.relay_calls.append((path, identity["id"]))
        if path == "/auth/me":
            return httpx.Response(200, json=identity)
        if path == "/workflows/" and request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {"id": "workflow-" + identity["id"], "workspace_id": identity["workspace_id"]}
                ],
            )
        return httpx.Response(403)

    async def register(self, method="none", callback=CALLBACK):
        response = await self.http.post(
            "/register",
            json={
                "redirect_uris": [callback],
                "token_endpoint_auth_method": method,
                "grant_types": ["authorization_code", "refresh_token"],
                "scope": "relay:read",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def params(self, client):
        return dict(
            client_id=client["client_id"],
            redirect_uri=client["redirect_uris"][0],
            response_type="code",
            code_challenge_method="S256",
            code_challenge=self.challenge,
            resource=PUBLIC + "/mcp",
            scope="relay:read",
            state="compatibility-state",
        )

    async def begin(self, client):
        response = await self.http.get("/authorize", params=self.params(client))
        self.assertEqual(response.status_code, 302)
        response = await self.http.get(response.headers["location"])
        self.assertEqual(response.status_code, 200)
        return response, Fields(response.text).values

    async def authorize_user(self, client, user="alice", referer_only=False):
        page, fields = await self.begin(client)
        headers = {"Referer": PUBLIC + "/oauth/consent"} if referer_only else {"Origin": PUBLIC}
        response = await self.http.post(
            "/oauth/login",
            headers=headers,
            data={
                **fields,
                "email": user + "@example.invalid",
                "password": secrets.token_urlsafe(24),
            },
        )
        self.assertEqual(response.status_code, 303)
        page = await self.http.get(response.headers["location"])
        fields = Fields(page.text).values
        response = await self.http.post(
            "/oauth/approve", headers=headers, data={**fields, "decision": "approve"}
        )
        self.assertEqual(response.status_code, 303)
        query = parse_qs(urlsplit(response.headers["location"]).query)
        self.assertEqual(query["state"], ["compatibility-state"])
        return query["code"][0]

    async def exchange(self, client, code):
        data = dict(
            grant_type="authorization_code",
            client_id=client["client_id"],
            code=code,
            redirect_uri=client["redirect_uris"][0],
            resource=PUBLIC + "/mcp",
            code_verifier=self.verifier,
        )
        headers = {}
        if client["token_endpoint_auth_method"] == "client_secret_post":
            data["client_secret"] = client["client_secret"]
        elif client["token_endpoint_auth_method"] == "client_secret_basic":
            encoded = base64.b64encode(
                (client["client_id"] + ":" + client["client_secret"]).encode()
            ).decode()
            headers["Authorization"] = "Basic " + encoded
        response = await self.http.post("/token", data=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        return response.json()

    async def rpc(self, token, method, params=None):
        return await self.http.post(
            "/mcp",
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/json, text/event-stream",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        )

    async def test_discovery_advertises_only_working_auth_methods(self):
        response = await self.http.get("/.well-known/oauth-authorization-server")
        metadata = response.json()
        self.assertEqual(
            set(metadata["token_endpoint_auth_methods_supported"]),
            {"none", "client_secret_post", "client_secret_basic"},
        )
        self.assertEqual(
            set(metadata["revocation_endpoint_auth_methods_supported"]),
            {"none", "client_secret_post", "client_secret_basic"},
        )
        self.assertFalse(metadata.get("client_id_metadata_document_supported", False))
        self.assertEqual(metadata["code_challenge_methods_supported"], ["S256"])
        for method in metadata["token_endpoint_auth_methods_supported"]:
            client = await self.register(method)
            pair = await self.exchange(client, await self.authorize_user(client))
            data = {"client_id": client["client_id"], "token": pair["access_token"]}
            auth = None
            if method == "client_secret_post":
                data["client_secret"] = client["client_secret"]
            elif method == "client_secret_basic":
                auth = httpx.BasicAuth(client["client_id"], client["client_secret"])
            revoked = await self.http.post("/revoke", data=data, auth=auth)
            self.assertEqual(revoked.status_code, 200)
            self.assertEqual((await self.rpc(pair["access_token"], "tools/list")).status_code, 401)
        response = await self.http.post(
            "/register",
            json={"redirect_uris": [CALLBACK], "token_endpoint_auth_method": "private_key_jwt"},
        )
        self.assertEqual(response.status_code, 400)

    async def test_public_full_flow_two_users_refresh_revocation(self):
        client = await self.register()
        first = await self.exchange(client, await self.authorize_user(client, referer_only=True))
        second = await self.exchange(client, await self.authorize_user(client, "bob"))
        initialized = await self.rpc(
            first["access_token"],
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "compat-test", "version": "1"},
            },
        )
        self.assertEqual(initialized.status_code, 200)
        self.assertIn("serverInfo", initialized.json()["result"])
        tools = await self.rpc(first["access_token"], "tools/list")
        self.assertEqual(len(tools.json()["result"]["tools"]), 16)
        for tokens, user in ((first, "alice"), (second, "bob")):
            listed = await self.rpc(
                tokens["access_token"],
                "tools/call",
                {"name": "relay_list_workflows", "arguments": {}},
            )
            self.assertIn("workspace-" + user, listed.text)
            for access in self.identities:
                self.assertNotIn(access, listed.text)
            denied = await self.rpc(
                tokens["access_token"],
                "tools/call",
                {"name": "relay_create_workflow", "arguments": {"name": "denied"}},
            )
            self.assertTrue(denied.json()["result"]["isError"])
        data = {
            "grant_type": "refresh_token",
            "client_id": client["client_id"],
            "refresh_token": first["refresh_token"],
            "resource": PUBLIC + "/mcp",
        }
        rotated = await self.http.post("/token", data=data)
        self.assertEqual(rotated.status_code, 200)
        self.assertEqual((await self.http.post("/token", data=data)).status_code, 400)
        self.assertEqual((await self.rpc(first["access_token"], "tools/list")).status_code, 401)
        access = rotated.json()["access_token"]
        self.assertEqual(
            (
                await self.http.post(
                    "/revoke", data={"client_id": client["client_id"], "token": access}
                )
            ).status_code,
            200,
        )
        self.assertEqual((await self.rpc(access, "tools/list")).status_code, 401)
        self.assertEqual((await self.rpc(second["access_token"], "tools/list")).status_code, 200)

    async def test_authorization_diagnostics_and_restart_recovery(self):
        client = await self.register()
        cases = [
            ("client_id", None, "client_id is required"),
            (
                "client_id",
                "unknown",
                "Unknown client registration; register again after a server restart",
            ),
            ("redirect_uri", CALLBACK + "/", "redirect_uri must exactly match a registered URI"),
            ("redirect_uri", None, "redirect_uri must exactly match a registered URI"),
            ("code_challenge_method", None, "code_challenge_method must be S256"),
            ("code_challenge_method", "plain", "code_challenge_method must be S256"),
            ("code_challenge", None, "A valid S256 code_challenge is required"),
            ("resource", None, "resource must exactly match this MCP endpoint"),
            ("resource", PUBLIC + "/other", "resource must exactly match this MCP endpoint"),
            ("scope", "admin", "Requested scopes must be supported and registered"),
            ("response_type", None, "response_type must be code"),
        ]
        for key, value, message in cases:
            with self.subTest(parameter=key, missing=value is None):
                params = self.params(client)
                if value is None:
                    params.pop(key)
                else:
                    params[key] = value
                response = await self.http.get("/authorize", params=params)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json().get("error_description"), message)
                self.assertNotIn(self.challenge, response.text)
        self.app.state.provider.clients.clear()  # A restart loses all registrations.
        response = await self.http.get("/authorize", params=self.params(client))
        self.assertIn("register again", response.json().get("error_description", ""))
        fresh = await self.register()
        await self.exchange(fresh, await self.authorize_user(fresh))

    async def test_post_authorize_and_duplicate_parameters(self):
        client = await self.register()
        params = self.params(client)
        response = await self.http.post("/authorize", data=params)
        self.assertEqual(response.status_code, 302)
        response = await self.http.get(
            "/authorize", params=[*params.items(), ("client_id", "duplicate")]
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error_description"],
            "Duplicate authorization parameters are not allowed",
        )
        self.assertNotIn("location", response.headers)

    async def test_browser_referer_fallback_and_csrf(self):
        client = await self.register()
        page, fields = await self.begin(client)
        self.assertEqual(page.headers["referrer-policy"], "same-origin")
        self.assertIn("secure", page.headers["set-cookie"].lower())
        for headers in (
            {},
            {"Origin": "https://evil.invalid", "Referer": PUBLIC + "/oauth/consent"},
            {"Origin": "null", "Referer": PUBLIC + "/oauth/consent"},
            {"Referer": "https://evil.invalid"},
            {"Referer": "https://[malformed"},
        ):
            for path in ("/oauth/login", "/oauth/approve"):
                response = await self.http.post(path, headers=headers, data=fields)
                self.assertEqual(response.status_code, 403)
        for path in ("/oauth/login", "/oauth/approve"):
            response = await self.http.post(
                path,
                headers={"Referer": PUBLIC + "/oauth/consent"},
                data={**fields, "csrf_token": "invalid"},
            )
            self.assertEqual(response.status_code, 403)

    async def test_redirect_encoding_and_registration_normalization(self):
        callback = CALLBACK + "?a=one%20two&b=%2F"
        client = await self.register(callback=callback)
        await self.exchange(client, await self.authorize_user(client))
        for redirect in (
            CALLBACK + "/",
            callback.replace("%20", "+"),
            callback.replace("%2F", "/"),
        ):
            response = await self.http.get(
                "/authorize", params={**self.params(client), "redirect_uri": redirect}
            )
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("location", response.headers)
        response = await self.http.post(
            "/register",
            json={"redirect_uris": ["https://CHATGPT.com"], "token_endpoint_auth_method": "none"},
        )
        self.assertEqual(response.status_code, 400)
