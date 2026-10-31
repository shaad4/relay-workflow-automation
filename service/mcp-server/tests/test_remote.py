import asyncio
import secrets
import time
from urllib.parse import parse_qs, urlsplit

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

    async def register_scope_profile(self, name, scopes=None, auth_method="none"):
        """Synthetic client profiles, not captured ChatGPT/Claude credentials or traffic."""
        body = {
            "client_name": name,
            "redirect_uris": [test_oauth.CALLBACK],
            "token_endpoint_auth_method": auth_method,
            "grant_types": ["authorization_code", "refresh_token"],
        }
        if scopes is not None:
            body["scope"] = " ".join(scopes)
        response = await self.http.post("/register", json=body)
        self.assertEqual(response.status_code, 201)
        registered = response.json()
        self.client = registered["client_id"]
        self.profile_secret = registered.get("client_secret")
        if hasattr(self, "requested_scope"):
            del self.requested_scope
        return registered

    async def grant_scope_profile(self, scopes=None):
        if scopes is None:
            if hasattr(self, "requested_scope"):
                del self.requested_scope
        else:
            self.requested_scope = " ".join(scopes)
        code = (await self.approve())["code"][0]
        expected = scopes if scopes is not None else ["relay:read"]
        return await self.exchange_scope_profile(code, expected)

    async def exchange_scope_profile(self, code, expected):
        self.assertEqual(self.provider.code_store.codes[code].scopes, expected)
        auth = {"client_secret": self.profile_secret} if self.profile_secret else {}
        response = await self.exchange(code, **auth)
        self.assertEqual(response.status_code, 200)
        pair = response.json()
        self.assertEqual(pair["scope"].split(), expected)
        access = await self.provider.load_access_token(pair["access_token"])
        self.assertEqual(access.scopes, expected)
        self.assertEqual(access.client_id, self.client)
        self.assertEqual(access.resource, RESOURCE)
        return pair

    async def assert_execution_scope_challenge(self, pair):
        before = len(self.calls)
        response = await self.call(
            pair["access_token"],
            "relay_run_workflow",
            {"workflow_id": "workflow-user-a", "input_data": {}},
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(len(self.calls), before, "Denied calls must not reach Relay")
        challenge = result["_meta"]["mcp/www_authenticate"]
        self.assertEqual(len(challenge), 1)
        self.assertIn('error="insufficient_scope"', challenge[0])
        self.assertIn('error_description="Authorize relay:execute to use this tool"', challenge[0])
        self.assertIn('scope="relay:execute"', challenge[0])
        self.assertIn(
            f'resource_metadata="{ORIGIN}/.well-known/oauth-protected-resource/mcp"',
            challenge[0],
        )
        self.assertNotIn("relay:write", response.text)
        self.assertNotIn("relay:delete", response.text)
        for credential in (pair["access_token"], pair["refresh_token"], self.profile_secret):
            if credential:
                self.assertNotIn(credential, response.text)
        for grant in self.provider.grants.values():
            self.assertNotIn(grant["session"].access_token, response.text)
            self.assertNotIn(grant["session"].refresh_token, response.text)

    async def test_remote_oauth_tool_metadata_matches_enforced_permissions(self):
        token = await self.mint(["relay:read"])
        for path in (
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource/mcp",
        ):
            metadata = (await self.http.get(path)).json()
            self.assertEqual(set(metadata["scopes_supported"]), set(SCOPES))
        response = await self.rpc("tools/list", token)
        for tool in response.json()["result"]["tools"]:
            scope = TOOL_SCOPES[tool["name"]]
            self.assertEqual(
                tool["_meta"]["securitySchemes"],
                [{"type": "oauth2", "scopes": [scope] if scope else []}],
            )

    async def test_remote_chatgpt_read_only_reconnect_does_not_grant_execution(self):
        # Also models legacy registrations that defaulted to read-only before this fix.
        registered = await self.register_scope_profile("ChatGPT", ["relay:read"])
        self.assertEqual(registered["scope"], "relay:read")
        for _ in range(2):
            pair = await self.grant_scope_profile()
            result = await self.call(pair["access_token"], "relay_list_workflows")
            self.assertFalse(result.json()["result"].get("isError", False))
            await self.assert_execution_scope_challenge(pair)

        # A challenge is not consent, nor permission to bypass client registration.
        self.requested_scope = "relay:read relay:execute"
        response = await self.http.get("/authorize", params=self.params())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_scope")
        self.assertIn("exceed this client registration", response.json()["error_description"])
        self.assertEqual((await self.provider.get_client(self.client)).scope, "relay:read")
        response = await self.http.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.client,
                "refresh_token": pair["refresh_token"],
                "scope": "relay:read relay:execute",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_scope")
        await self.assert_execution_scope_challenge(pair)

        # Recreating the client with the needed scopes plus fresh consent resolves it.
        old_client = self.client
        await self.register_scope_profile("ChatGPT", ["relay:read", "relay:execute"])
        self.assertNotEqual(self.client, old_client)
        authorized = await self.grant_scope_profile(["relay:read", "relay:execute"])
        response = await self.call(
            authorized["access_token"],
            "relay_run_workflow",
            {"workflow_id": "workflow-user-a", "input_data": {}},
        )
        self.assertFalse(response.json()["result"].get("isError", False))
        await self.assert_execution_scope_challenge(pair)

    async def test_remote_dcr_defaults_do_not_grant_or_refresh_privileges(self):
        for name in ("ChatGPT", "Claude"):
            with self.subTest(client=name):
                before = set(self.provider.access_tokens)
                registered = await self.register_scope_profile(name)
                self.assertEqual(set(registered["scope"].split()), set(SCOPES))
                stored = await self.provider.get_client(self.client)
                self.assertEqual(stored.scope, registered["scope"])
                self.assertEqual(set(self.provider.access_tokens), before)

                # Eligible permissions are not issued when authorization omits scope.
                pair = await self.grant_scope_profile()
                await self.assert_execution_scope_challenge(pair)
                before = set(self.provider.access_tokens)
                self.requested_scope = "relay:read relay:write relay:delete relay:execute"
                denied = await self.approve(decision="deny")
                self.assertEqual(denied["error"], ["access_denied"])
                self.assertNotIn("code", denied)
                self.assertFalse(self.provider.code_store.codes)
                self.assertEqual(set(self.provider.access_tokens), before)
                response = await self.http.post(
                    "/token",
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.client,
                        "refresh_token": pair["refresh_token"],
                        "scope": self.requested_scope,
                    },
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_scope")
                await self.assert_execution_scope_challenge(pair)

    async def test_remote_all_supported_scopes_require_consent_and_survive_refresh(self):
        # Exact scope order observed in ChatGPT's authorization request.
        requested = ["relay:read", "relay:write", "relay:delete", "relay:execute"]
        for name, auth_method in (("ChatGPT", "client_secret_post"), ("Claude", "none")):
            for registration_scopes in (None, requested):
                with self.subTest(client=name, registration_scopes=registration_scopes):
                    registered = await self.register_scope_profile(
                        name, registration_scopes, auth_method
                    )
                    self.assertEqual(set(registered["scope"].split()), set(requested))
                    self.assertEqual(
                        (await self.provider.get_client(self.client)).scope, registered["scope"]
                    )
                    self.requested_scope = " ".join(requested)
                    before = set(self.provider.access_tokens)
                    form = await self.begin()
                    page = await self.http.get(
                        "/oauth/consent", params={"request_id": form["request_id"]}
                    )
                    for label in (
                        "View workflows and execution history",
                        "Create and modify workflows",
                        "Delete workflows and nodes",
                        "Publish and execute workflows",
                    ):
                        self.assertIn(label, page.text)
                    self.assertFalse(self.provider.code_store.codes)
                    self.assertEqual(set(self.provider.access_tokens), before)
                    # Registration and a scope request cannot replace login/approval.
                    response = await self.http.post(
                        "/oauth/approve",
                        data={**form, "decision": "approve"},
                        headers={"Origin": ORIGIN},
                    )
                    self.assertEqual(response.status_code, 401)
                    form = await self.login(form)
                    self.assertFalse(self.provider.code_store.codes)
                    self.assertEqual(set(self.provider.access_tokens), before)
                    response = await self.http.post(
                        "/oauth/approve",
                        data={**form, "decision": "approve"},
                        headers={"Origin": ORIGIN},
                    )
                    self.assertEqual(response.status_code, 303)
                    code = parse_qs(urlsplit(response.headers["location"]).query)["code"][0]
                    pair = await self.exchange_scope_profile(code, requested)
                    auth = {"client_secret": self.profile_secret} if self.profile_secret else {}
                    refreshed = await self.http.post(
                        "/token",
                        data={
                            "grant_type": "refresh_token",
                            "client_id": self.client,
                            "refresh_token": pair["refresh_token"],
                            **auth,
                        },
                    )
                    self.assertEqual(refreshed.status_code, 200)
                    self.assertEqual(refreshed.json()["scope"].split(), requested)
                    access = await self.provider.load_access_token(refreshed.json()["access_token"])
                    self.assertEqual(access.scopes, requested)
                    self.assertEqual(access.resource, RESOURCE)
                    response = await self.call(
                        refreshed.json()["access_token"],
                        "relay_run_workflow",
                        {"workflow_id": "workflow-user-a", "input_data": {}},
                    )
                    self.assertFalse(response.json()["result"].get("isError", False))

    async def test_remote_registration_and_authorization_reject_unsupported_scopes(self):
        for invalid in ("relay:read admin", "relay:read,relay:execute", "relay:Execute"):
            with self.subTest(scope=invalid):
                before = set(self.provider.clients)
                response = await self.http.post(
                    "/register",
                    json={
                        "redirect_uris": [test_oauth.CALLBACK],
                        "token_endpoint_auth_method": "none",
                        "grant_types": ["authorization_code", "refresh_token"],
                        "scope": invalid,
                    },
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(set(self.provider.clients), before)
                await self.register_scope_profile("ChatGPT")
                self.requested_scope = invalid
                response = await self.http.get("/authorize", params=self.params())
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_scope")
                self.assertEqual(
                    response.json()["error_description"], "Requested scopes are not supported"
                )
                self.assertFalse(self.provider.authorization_store.requests)
                self.assertFalse(self.provider.access_tokens)

    async def test_remote_chatgpt_and_claude_explicit_scopes_and_refresh(self):
        client_ids = set()
        for name, auth_method in (("ChatGPT", "client_secret_post"), ("Claude", "none")):
            with self.subTest(client=name):
                await self.register_scope_profile(
                    name, ["relay:read", "relay:execute"], auth_method
                )
                client_ids.add(self.client)
                # Eligible client scopes never become grants merely through registration.
                read_pair = await self.grant_scope_profile()
                await self.assert_execution_scope_challenge(read_pair)
                pair = await self.grant_scope_profile(["relay:read", "relay:execute"])
                before = len(self.calls)
                response = await self.call(
                    pair["access_token"],
                    "relay_run_workflow",
                    {
                        "workflow_id": "workflow-user-a",
                        "input_data": {},
                    },
                )
                self.assertFalse(response.json()["result"].get("isError", False))
                self.assertGreater(len(self.calls), before)
                auth = {"client_secret": self.profile_secret} if self.profile_secret else {}
                refreshed = await self.http.post(
                    "/token",
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.client,
                        "refresh_token": pair["refresh_token"],
                        **auth,
                    },
                )
                self.assertEqual(refreshed.status_code, 200)
                self.assertEqual(refreshed.json()["scope"], "relay:read relay:execute")
                response = await self.call(
                    refreshed.json()["access_token"],
                    "relay_run_workflow",
                    {"workflow_id": "workflow-user-a", "input_data": {}},
                )
                self.assertFalse(response.json()["result"].get("isError", False))
                before = len(self.calls)
                denied = await self.call(
                    refreshed.json()["access_token"],
                    "relay_delete_workflow",
                    {
                        "workflow_id": "workflow-user-a",
                    },
                )
                self.assertTrue(denied.json()["result"]["isError"])
                self.assertEqual(len(self.calls), before)
                reduced = await self.http.post(
                    "/token",
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.client,
                        "refresh_token": refreshed.json()["refresh_token"],
                        "scope": "relay:read",
                        **auth,
                    },
                )
                self.assertEqual(reduced.status_code, 200)
                self.assertEqual(reduced.json()["scope"], "relay:read")
                await self.assert_execution_scope_challenge(reduced.json())
        self.assertEqual(len(client_ids), 2)

    async def test_remote_scope_upgrade_requires_consent_and_cannot_be_forged(self):
        await self.register_scope_profile("ChatGPT", ["relay:read", "relay:execute"])
        pair = await self.grant_scope_profile(["relay:read"])
        self.requested_scope = "relay:read relay:execute"
        form = await self.begin()
        page = await self.http.get("/oauth/consent", params={"request_id": form["request_id"]})
        self.assertIn("Publish and execute workflows", page.text)
        self.assertNotIn("Delete workflows and nodes", page.text)
        form = await self.login(form)
        denied = await self.http.post(
            "/oauth/approve", data={**form, "decision": "deny"}, headers={"Origin": ORIGIN}
        )
        self.assertIn("access_denied", denied.headers["location"])
        await self.assert_execution_scope_challenge(pair)
        before = len(self.calls)
        forged = await self.rpc(
            "tools/call",
            pair["access_token"],
            {
                "name": "relay_run_workflow",
                "arguments": {"workflow_id": "workflow-user-a", "input_data": {}},
                "_meta": {"securitySchemes": [{"type": "oauth2", "scopes": SCOPES}]},
            },
        )
        self.assertTrue(forged.json()["result"]["isError"])
        self.assertEqual(len(self.calls), before)

    async def test_remote_client_names_do_not_change_scope_or_audience_rules(self):
        for name in ("ChatGPT", "Claude"):
            with self.subTest(client=name):
                await self.register_scope_profile(name, ["relay:read", "relay:execute"])
                for invalid in ("relay:read,relay:execute", "relay:read relay:Execute", "admin"):
                    self.requested_scope = invalid
                    response = await self.http.get("/authorize", params=self.params())
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["error"], "invalid_scope")
                self.requested_scope = "relay:read relay:execute"
                response = await self.http.get(
                    "/authorize",
                    params={
                        **self.params(),
                        "resource": "https://other.invalid/mcp",
                    },
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "invalid_target")

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
