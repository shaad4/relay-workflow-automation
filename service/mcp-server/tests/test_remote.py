import asyncio
import secrets
import time

import httpx
import test_oauth
from oauth.scopes import SCOPES, TOOL_SCOPES
from remote_server import create_remote_app
from test_oauth import ORIGIN, RESOURCE


class RemoteTests(test_oauth.OAuthTests):
    """Run the OAuth regression suite on the combined app as well as MCP tests."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.http.aclose()
        self.calls = []
        self.rejected_users = set()
        self.changed_workspace = False
        self.leak = False
        self.timeout_mutation = False
        self.app = create_remote_app(
            provider=self.provider,
            session_secret=secrets.token_urlsafe(32),
            relay_transport=httpx.MockTransport(self.relay),
        )
        self.lifespan = self.app.router.lifespan_context(self.app)
        self.started = asyncio.Event()
        self.stopped = asyncio.Event()

        async def run_lifespan():
            async with self.lifespan:
                self.started.set()
                await self.stopped.wait()

        self.lifespan_task = asyncio.create_task(run_lifespan())
        await asyncio.wait_for(self.started.wait(), 5)
        self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url=ORIGIN)

    async def asyncTearDown(self):
        await self.http.aclose()
        self.stopped.set()
        await self.lifespan_task
        self.env.stop()

    async def relay(self, request):
        session = next(
            (
                g["session"]
                for g in self.provider.grants.values()
                if request.headers.get("authorization") == "Bearer " + g["session"].access_token
            ),
            None,
        )
        if session is None:
            return httpx.Response(401)
        self.calls.append((request.method, request.url.path, session.user_id))
        if session.user_id in self.rejected_users:
            return httpx.Response(401, json={"detail": session.access_token})
        if request.url.path == "/auth/me":
            return httpx.Response(
                200,
                json={
                    "id": session.user_id,
                    "workspace_id": "changed" if self.changed_workspace else session.workspace_id,
                },
            )
        if self.timeout_mutation and request.method == "POST":
            raise httpx.ReadTimeout(session.access_token)
        if "workflow-other" in request.url.path:
            return httpx.Response(403, json={"detail": session.refresh_token})
        if self.leak:
            return httpx.Response(
                200,
                json=[
                    {
                        "access_token": session.access_token,
                        "nested": {"detail": "secret " + session.refresh_token},
                    }
                ],
            )
        if request.url.path == "/workflows/":
            data = {"id": "workflow-" + session.user_id, "workspace_id": session.workspace_id}
            return httpx.Response(200, json=[data] if request.method == "GET" else data)
        return httpx.Response(200, json={"valid": True, "success": True})

    async def mint(self, scopes=None, user="user-a"):
        # Register requested scopes through the real OAuth registration endpoint.
        response = await self.http.post(
            "/register",
            json={
                "redirect_uris": ["http://127.0.0.1:9000/callback"],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "scope": " ".join(scopes if scopes is not None else SCOPES),
            },
        )
        self.assertEqual(response.status_code, 201)
        self.client = response.json()["client_id"]
        self.requested_scope = response.json()["scope"]
        code = (await self.approve(user=user))["code"][0]
        response = await self.exchange(code)
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def params(self, **overrides):
        params = super().params(**overrides)
        if hasattr(self, "requested_scope"):
            params["scope"] = self.requested_scope
        return params

    async def rpc(self, method, token=None, params=None, headers=None):
        request_headers = {"Accept": "application/json, text/event-stream"}
        if token:
            request_headers["Authorization"] = "Bearer " + token
        request_headers.update(headers or {})
        return await self.http.post(
            "/mcp",
            headers=request_headers,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        )

    async def call(self, token, name, arguments=None):
        return await self.rpc("tools/call", token, {"name": name, "arguments": arguments or {}})

    async def test_remote_rejects_nonlocal_peers_and_mismatched_resource(self):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app, client=("192.0.2.10", 1234)),
            base_url=ORIGIN,
        ) as remote:
            self.assertEqual(
                (await remote.get("/.well-known/oauth-authorization-server")).status_code, 403
            )
        self.provider.resource = "https://other.invalid/mcp"
        with self.assertRaises(ValueError):
            create_remote_app(provider=self.provider, session_secret=secrets.token_urlsafe(32))

    async def test_remote_initialization_discovery_metadata(self):
        token = await self.mint(["relay:read"])
        response = await self.rpc(
            "initialize",
            token,
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("serverInfo", response.json()["result"])
        response = await self.rpc("tools/list", token)
        tools = response.json()["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, set(TOOL_SCOPES))
        for tool in tools:
            self.assertNotIn("workspace_id", tool["inputSchema"].get("properties", {}))
            self.assertNotIn("user_id", tool["inputSchema"].get("properties", {}))
        metadata = (await self.http.get("/.well-known/oauth-protected-resource/mcp")).json()
        self.assertEqual(metadata["resource"], RESOURCE)
        self.assertEqual(set(metadata["scopes_supported"]), set(SCOPES))

    async def test_remote_missing_invalid_expired_revoked_wrong_audience(self):
        for token in (None, secrets.token_urlsafe(32)):
            response = await self.rpc("tools/list", token)
            self.assertEqual(response.status_code, 401)
            self.assertIn("resource_metadata", response.headers["www-authenticate"])
        token = await self.mint()
        record = self.provider.access_tokens[token]
        record.resource = "https://other.invalid/mcp"
        self.assertEqual((await self.rpc("tools/list", token)).status_code, 401)
        record.resource = RESOURCE
        record.expires_at = int(time.time()) - 1
        self.assertEqual((await self.call(token, "relay_list_workflows")).status_code, 401)
        token = await self.mint()
        await self.http.post("/revoke", data={"client_id": self.client, "token": token})
        self.assertEqual((await self.call(token, "relay_list_workflows")).status_code, 401)
        self.assertFalse(self.calls)

    async def test_remote_scope_enforcement_all_tools(self):
        tokens = {scope: await self.mint([scope]) for scope in SCOPES}
        arguments = {
            "name": "demo",
            "description": "demo",
            "workflow_id": "workflow-user-a",
            "version": 1,
            "node_id": "node-a",
            "node_type": "trigger",
            "configuration": {},
            "source_node_id": "node-a",
            "target_node_id": "node-b",
            "edge_id": "edge-a",
            "input_data": {},
            "execution_id": "execution-a",
            "page": 1,
            "nodes": [{"node_id": "node-a", "node_type": "trigger"}],
            "edges": [],
        }
        schemas = (await self.rpc("tools/list", tokens["relay:read"])).json()["result"]["tools"]
        for tool in schemas:
            name = tool["name"]
            args = {key: arguments[key] for key in tool["inputSchema"].get("properties", {})}
            for scope, token in tokens.items():
                before = len(self.calls)
                response = await self.call(token, name, args)
                self.assertEqual(response.status_code, 200)
                allowed = TOOL_SCOPES[name] in (None, scope)
                self.assertEqual(
                    response.json()["result"].get("isError", False), not allowed, (name, scope)
                )
                if not allowed:
                    self.assertEqual(len(self.calls), before)

    async def test_remote_two_users_workspace_and_cross_workspace_denial(self):
        first, second = await self.mint(user="user-a"), await self.mint(user="user-b")
        results = await asyncio.gather(
            self.call(first, "relay_list_workflows"), self.call(second, "relay_list_workflows")
        )
        self.assertIn("workspace-user-a", results[0].text)
        self.assertNotIn("workspace-user-b", results[0].text)
        self.assertIn("workspace-user-b", results[1].text)
        response = await self.call(
            first, "relay_delete_workflow", {"workflow_id": "workflow-other"}
        )
        self.assertTrue(response.json()["result"]["isError"])
        self.assertEqual(self.calls[-1], ("DELETE", "/workflows/workflow-other/", "user-a"))

    async def test_remote_relay_revoked_expired_and_changed_identity(self):
        token = await self.mint()
        self.rejected_users.add("user-a")
        response = await self.call(token, "relay_create_workflow", {"name": "demo"})
        self.assertTrue(response.json()["result"]["isError"])
        self.assertTrue(all(path == "/auth/me" for _, path, _ in self.calls))
        self.rejected_users.clear()
        self.changed_workspace = True
        response = await self.call(token, "relay_list_workflows")
        self.assertTrue(response.json()["result"]["isError"])
        self.assertTrue(all(path == "/auth/me" for _, path, _ in self.calls))

    async def test_remote_identifiers_and_untrusted_workspace_arguments(self):
        token = await self.mint()
        for identifier in ("..", "../other", "workflow-a?workspace_id=other", "a%2fb"):
            response = await self.call(token, "relay_delete_workflow", {"workflow_id": identifier})
            self.assertTrue(response.json()["result"]["isError"])
        self.assertFalse(any(method == "DELETE" for method, _, _ in self.calls))
        response = await self.call(
            token, "relay_list_workflows", {"workspace_id": "other", "user_id": "other"}
        )
        self.assertEqual(response.json()["error"]["code"], -32602)
        # Explicit identity overrides are rejected before the SDK drops extra fields.
        self.assertNotIn("workspace-other", response.text)
        self.assertTrue(all(user == "user-a" for _, _, user in self.calls))

    async def test_remote_complete_workflow_stops_after_uncertain_mutation(self):
        token = await self.mint(["relay:write"])
        self.timeout_mutation = True
        response = await self.call(
            token,
            "relay_create_complete_workflow",
            {
                "name": "demo",
                "description": "demo",
                "nodes": [{"node_id": "start", "node_type": "trigger"}],
                "edges": [],
            },
        )
        self.assertTrue(response.json()["result"]["isError"])
        self.assertEqual(sum(method == "POST" for method, _, _ in self.calls), 1)

    async def test_remote_cookie_and_client_isolation(self):
        first, second = await self.mint(user="user-a"), await self.mint(user="user-b")
        seen_cookies = []
        original = self.relay

        async def cookie_relay(request):
            seen_cookies.append(request.headers.get("cookie"))
            result = await original(request)
            result.headers["set-cookie"] = "private_cookie=synthetic; Path=/"
            return result

        # A new application shares only the provider's records, never HTTP clients.
        other = create_remote_app(
            provider=self.provider,
            session_secret=secrets.token_urlsafe(32),
            relay_transport=httpx.MockTransport(cookie_relay),
        )
        async with other.router.lifespan_context(other):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=other), base_url=ORIGIN
            ) as client:
                for token in (first, second, first):
                    before = len(seen_cookies)
                    response = await client.post(
                        "/mcp",
                        headers={
                            "Authorization": "Bearer " + token,
                            "Accept": "application/json, text/event-stream",
                        },
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {"name": "relay_list_workflows", "arguments": {}},
                        },
                    )
                    self.assertFalse(response.json()["result"].get("isError", False))
                    self.assertIsNone(seen_cookies[before])

    async def test_remote_no_leakage_no_retry_and_origin(self):
        token = await self.mint()
        self.leak = True
        response = await self.call(token, "relay_list_workflows")
        self.assertFalse(response.json()["result"].get("isError", False))
        self.assertIn("[redacted]", response.text)
        self.leak = False
        self.timeout_mutation = True
        response = await self.call(token, "relay_create_workflow", {"name": "demo"})
        self.assertTrue(response.json()["result"]["isError"])
        self.assertEqual(sum(method == "POST" for method, _, _ in self.calls), 1)
        for grant in self.provider.grants.values():
            for credential in (
                grant["session"].access_token,
                grant["session"].refresh_token,
                token,
            ):
                self.assertNotIn(credential, response.text)
        response = await self.rpc("tools/list", token, headers={"Origin": "https://evil.invalid"})
        self.assertEqual(response.status_code, 403)
