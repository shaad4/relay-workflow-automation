import asyncio
import base64
import hashlib
import os
import re
import secrets
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oauth.app import create_oauth_app

ORIGIN = "http://127.0.0.1:8001"
CALLBACK = "http://127.0.0.1:9000/callback"
RESOURCE = ORIGIN + "/mcp"


class OAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {"RELAY_API_URL": "https://relay.invalid"})
        self.env.start()
        self.app = create_oauth_app(session_secret=secrets.token_urlsafe(32))
        self.provider = self.app.state.provider
        self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url=ORIGIN)
        self.client = await self.register()
        self.verifier = secrets.token_urlsafe(48)
        self.challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )

    async def asyncTearDown(self):
        await self.http.aclose()
        self.env.stop()

    async def register(self):
        response = await self.http.post(
            "/register",
            json={
                "redirect_uris": [CALLBACK],
                "token_endpoint_auth_method": "none",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["client_id"]

    def params(self, **overrides):
        return dict(
            client_id=self.client,
            redirect_uri=CALLBACK,
            response_type="code",
            code_challenge=self.challenge,
            code_challenge_method="S256",
            resource=RESOURCE,
            state="test-state",
            **overrides,
        )

    async def begin(self):
        response = await self.http.get("/authorize", params=self.params())
        self.assertEqual(response.status_code, 302)
        page = await self.http.get(response.headers["location"])
        self.assertEqual(page.status_code, 200)
        return {
            key: re.search(r'name="' + key + r'"\s+value="([^"]+)"', page.text).group(1)
            for key in ("request_id", "csrf_token")
        }

    async def login(self, form, user="user-a"):
        identity = {
            "user_id": user,
            "workspace_id": "workspace-" + user,
            "access_token": secrets.token_urlsafe(32),
            "refresh_token": secrets.token_urlsafe(32),
        }
        with patch("oauth.login.authenticate_relay_user", new=AsyncMock(return_value=identity)):
            response = await self.http.post(
                "/oauth/login",
                data={**form, "email": "demo@example.invalid", "password": "unused"},
                headers={"Origin": ORIGIN},
            )
        self.assertEqual(response.status_code, 303)
        page = await self.http.get(response.headers["location"])
        form["csrf_token"] = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text).group(1)
        for value in (identity["access_token"], identity["refresh_token"]):
            self.assertNotIn(value, page.text)
            self.assertNotIn(value, response.headers.get("set-cookie", ""))
        return form

    async def approve(self, decision="approve", user="user-a"):
        form = await self.login(await self.begin(), user)
        response = await self.http.post(
            "/oauth/approve", data={**form, "decision": decision}, headers={"Origin": ORIGIN}
        )
        self.assertEqual(response.status_code, 303)
        query = parse_qs(urlsplit(response.headers["location"]).query)
        self.assertEqual(query["state"], ["test-state"])
        return query

    async def exchange(self, code, **overrides):
        data = dict(
            grant_type="authorization_code",
            client_id=self.client,
            code=code,
            redirect_uri=CALLBACK,
            code_verifier=self.verifier,
            resource=RESOURCE,
        )
        data.update(overrides)
        return await self.http.post("/token", data=data)

    async def test_success_and_session_binding(self):
        code = (await self.approve())["code"][0]
        delegated = self.provider.code_store.codes[code].relay_session
        response = await self.exchange(code)
        self.assertEqual(response.status_code, 200)
        access = await self.provider.load_access_token(response.json()["access_token"])
        self.assertEqual(access.subject, "user-a")
        self.assertEqual(access.resource, RESOURCE)
        self.assertIs(self.provider.grants[access.grant_id]["session"], delegated)
        code2 = (await self.approve(user="user-b"))["code"][0]
        second = await self.exchange(code2)
        other = await self.provider.load_access_token(second.json()["access_token"])
        self.assertEqual(other.subject, "user-b")
        self.assertIsNot(self.provider.grants[other.grant_id]["session"], delegated)
        self.assertFalse(self.provider.login_store.sessions)

    async def test_invalid_pkce_wrong_client_redirect_and_resource(self):
        code = (await self.approve())["code"][0]
        other = await self.register()
        for overrides in (
            {"code_verifier": secrets.token_urlsafe(48)},
            {"code_verifier": "short"},
            {"client_id": other},
            {"redirect_uri": CALLBACK + "/"},
            {"resource": "https://other.invalid/mcp"},
        ):
            with self.subTest(fields=list(overrides)):
                self.assertEqual((await self.exchange(code, **overrides)).status_code, 400)
        self.assertEqual((await self.exchange(code)).status_code, 200)

    async def test_expired_reused_and_concurrent_codes(self):
        code = (await self.approve())["code"][0]
        self.provider.code_store.codes[code].expires_at = time.time() - 1
        self.assertEqual((await self.exchange(code)).status_code, 400)
        code = (await self.approve())["code"][0]
        responses = await asyncio.gather(self.exchange(code), self.exchange(code))
        self.assertEqual(sorted(r.status_code for r in responses), [200, 400])
        self.assertEqual((await self.exchange(code)).status_code, 400)

    async def test_denied_consent(self):
        result = await self.approve("deny")
        self.assertEqual(result["error"], ["access_denied"])
        self.assertNotIn("code", result)
        self.assertFalse(self.provider.code_store.codes)
        self.assertFalse(self.provider.login_store.sessions)

    async def test_refresh_rotation_and_revocation(self):
        pair = (await self.exchange((await self.approve())["code"][0])).json()
        data = dict(
            grant_type="refresh_token", client_id=self.client, refresh_token=pair["refresh_token"]
        )
        other = await self.register()
        for override in (
            {"client_id": other},
            {"resource": "https://other.invalid"},
            {"scope": "admin"},
        ):
            self.assertEqual(
                (await self.http.post("/token", data={**data, **override})).status_code, 400
            )
        rotated = await self.http.post("/token", data=data)
        self.assertEqual(rotated.status_code, 200)
        self.assertIsNone(await self.provider.load_access_token(pair["access_token"]))
        self.assertEqual((await self.http.post("/token", data=data)).status_code, 400)
        pair = rotated.json()
        # Wrong-client revocation is a successful no-op, as RFC 7009 requires.
        await self.http.post("/revoke", data={"client_id": other, "token": pair["access_token"]})
        self.assertIsNotNone(await self.provider.load_access_token(pair["access_token"]))
        revoked = await self.http.post(
            "/revoke", data={"client_id": self.client, "token": pair["access_token"]}
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertIsNone(await self.provider.load_access_token(pair["access_token"]))
        self.assertEqual(
            (
                await self.http.post(
                    "/token", data={**data, "refresh_token": pair["refresh_token"]}
                )
            ).status_code,
            400,
        )
        self.assertFalse(self.provider.grants)

    async def test_csrf_origin_and_consent_replay(self):
        form = await self.begin()
        for headers, submitted in (
            ({}, form),
            ({"Origin": "https://evil.invalid"}, form),
            ({"Origin": ORIGIN}, {**form, "csrf_token": "wrong"}),
        ):
            response = await self.http.post("/oauth/login", data=submitted, headers=headers)
            self.assertEqual(response.status_code, 403)
        form = await self.login(form)
        self.assertEqual(
            (
                await self.http.post("/oauth/approve", data={**form, "decision": "approve"})
            ).status_code,
            403,
        )
        for decision, status in (("unknown", 400), ("approve", 303), ("approve", 403)):
            response = await self.http.post(
                "/oauth/approve", data={**form, "decision": decision}, headers={"Origin": ORIGIN}
            )
            self.assertEqual(response.status_code, status)

    async def test_authorize_validation(self):
        for override in (
            {"redirect_uri": CALLBACK + "/"},
            {"redirect_uri": CALLBACK.replace("127.0.0.1", "localhost")},
            {"code_challenge_method": "plain"},
            {"code_challenge": "short"},
            {"resource": "https://other.invalid"},
        ):
            response = await self.http.get("/authorize", params={**self.params(), **override})
            self.assertIn(response.status_code, (400, 302))
            self.assertNotIn("/oauth/consent", response.headers.get("location", ""))
        response = await self.http.get(
            "/authorize", params={**self.params(), "redirect_uri": "HTTP://127.0.0.1:9000/callback"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("location", response.headers)

    async def test_confidential_client_authentication(self):
        response = await self.http.post(
            "/register",
            json={
                "redirect_uris": [CALLBACK],
                "token_endpoint_auth_method": "client_secret_post",
                "grant_types": ["authorization_code", "refresh_token"],
            },
        )
        self.assertEqual(response.status_code, 201)
        registered = response.json()
        self.client = registered["client_id"]
        code = (await self.approve())["code"][0]
        self.assertEqual((await self.exchange(code)).status_code, 401)
        self.assertEqual((await self.exchange(code, client_secret="incorrect")).status_code, 401)
        result = await self.exchange(code, client_secret=registered["client_secret"])
        self.assertEqual(result.status_code, 200)
        result = await self.http.post(
            "/revoke",
            data={
                "client_id": self.client,
                "client_secret": registered["client_secret"],
                "token": result.json()["refresh_token"],
            },
        )
        self.assertEqual(result.status_code, 200)
        self.assertFalse(self.provider.grants)

    async def test_expired_browser_state_and_login_failure(self):
        form = await self.begin()
        with patch(
            "oauth.login.authenticate_relay_user",
            new=AsyncMock(side_effect=httpx.ConnectError("unavailable")),
        ):
            response = await self.http.post("/oauth/login", data=form, headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self.provider.login_store.sessions)
        self.provider.authorization_store.requests[form["request_id"]].expires_at = time.time() - 1
        response = await self.http.post("/oauth/login", data=form, headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 400)
        # A stale signed browser cookie must not prevent starting a fresh flow.
        new = await self.begin()
        self.assertNotEqual(form["request_id"], new["request_id"])

    async def test_expired_access_and_refresh_tokens(self):
        pair = (await self.exchange((await self.approve())["code"][0])).json()
        self.provider.access_tokens[pair["access_token"]].expires_at = int(time.time()) - 1
        self.assertIsNone(await self.provider.load_access_token(pair["access_token"]))
        self.provider.refresh_tokens[pair["refresh_token"]].expires_at = int(time.time()) - 1
        response = await self.http.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.client,
                "refresh_token": pair["refresh_token"],
            },
        )
        self.assertEqual(response.status_code, 400)

    async def test_expiry_cleanup_and_local_only(self):
        pair = (await self.exchange((await self.approve())["code"][0])).json()
        access = await self.provider.load_access_token(pair["access_token"])
        self.provider.grants[access.grant_id]["expires_at"] = time.time() - 1
        self.assertIsNone(await self.provider.load_access_token(pair["access_token"]))
        self.assertFalse(self.provider.refresh_tokens)
        with self.assertRaises(ValueError):
            create_oauth_app(
                public_origin="https://public.invalid", session_secret=secrets.token_urlsafe(32)
            )


if __name__ == "__main__":
    unittest.main()
