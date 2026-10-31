"""OAuth presentation contracts; Relay authentication stays mocked."""

import unittest
from html import escape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import httpx
import test_oauth
from oauth.consent import HTML_CSP
from remote_server import create_remote_app


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def named(self, name):
        return [attrs for tag, attrs in self.tags if tag == name]


class OAuthPageTests(unittest.IsolatedAsyncioTestCase):
    # Reuse setup and flow helpers without re-running the base class's tests.
    asyncSetUp = test_oauth.OAuthTests.asyncSetUp
    asyncTearDown = test_oauth.OAuthTests.asyncTearDown
    register = test_oauth.OAuthTests.register
    params = test_oauth.OAuthTests.params
    begin = test_oauth.OAuthTests.begin
    login = test_oauth.OAuthTests.login

    async def page(self, form):
        return await self.http.get("/oauth/consent", params={"request_id": form["request_id"]})

    def assert_page_security(self, page, form):
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.headers["cache-control"], "no-store")
        self.assertEqual(page.headers["pragma"], "no-cache")
        self.assertEqual(page.headers["referrer-policy"], "same-origin")
        policy = page.headers["content-security-policy"]
        for directive in (
            "default-src 'none'",
            "style-src 'self'",
            "base-uri 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
        ):
            self.assertIn(directive, policy)
        self.assertNotIn("unsafe-inline", policy)
        self.assertNotIn("script-src", policy)  # Falls back to default-src 'none'.
        elements = Elements(page.text)
        self.assertIn("img-src 'self'", policy)
        self.assertEqual(
            elements.named("img"),
            [
                {
                    "class": "logo",
                    "src": "/oauth/static/relay-light.png",
                    "alt": "Relay",
                    "width": "1983",
                    "height": "793",
                }
            ],
        )
        self.assertFalse(elements.named("style"))
        self.assertFalse(elements.named("script"))
        self.assertTrue(all("style" not in attrs for _, attrs in elements.tags))
        self.assertTrue(
            all(not key.startswith("on") for _, attrs in elements.tags for key in attrs)
        )
        self.assertEqual(
            elements.named("link"), [{"rel": "stylesheet", "href": "/oauth/static/relay.css"}]
        )
        hidden = {
            item["name"]: item["value"]
            for item in elements.named("input")
            if item.get("type") == "hidden"
        }
        self.assertEqual(hidden, form)
        return elements

    async def test_login_design_and_escaped_application_name(self):
        name = '<script>alert("untrusted")</script> & Application'
        self.provider.clients[self.client].client_name = name
        form = await self.begin()
        page = await self.page(form)
        elements = self.assert_page_security(page, form)
        self.assertEqual(page.headers["content-security-policy"], HTML_CSP)
        self.assertIn(escape(name), page.text)
        self.assertNotIn(name, page.text)
        self.assertIn("Connect to Relay", page.text)
        self.assertIn("Continue with Relay", page.text)
        self.assertIn("View workflows and execution history", page.text)
        self.assertIn("Registration does not mean Relay has verified", page.text)
        self.assertEqual(elements.named("form"), [{"method": "POST", "action": "/oauth/login"}])
        self.assertNotIn('value="approve"', page.text)
        self.assertEqual({item["for"] for item in elements.named("label")}, {"email", "password"})
        password = next(item for item in elements.named("input") if item.get("name") == "password")
        self.assertEqual(password["type"], "password")
        self.assertEqual(password["autocomplete"], "current-password")
        self.assertNotIn("value", password)

    async def test_consent_design_and_approve(self):
        form = await self.login(await self.begin())
        page = await self.page(form)
        elements = self.assert_page_security(page, form)
        self.assertNotIn('type="password"', page.text)
        self.assertIn("Signed in to Relay", page.text)
        self.assertIn("Approve access", page.text)
        self.assertEqual(elements.named("form"), [{"method": "POST", "action": "/oauth/approve"}])
        self.assertEqual({b["value"] for b in elements.named("button")}, {"approve", "deny"})
        self.assertEqual(
            page.headers["content-security-policy"],
            HTML_CSP.replace("form-action 'self'", "form-action 'self' " + test_oauth.CALLBACK),
        )
        response = await self.http.post(
            "/oauth/approve",
            data={**form, "decision": "approve"},
            headers={"Origin": test_oauth.ORIGIN},
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("code", parse_qs(urlsplit(response.headers["location"]).query))
        self.assertEqual(len(self.provider.code_store.codes), 1)

    async def test_deny_and_csrf_protection(self):
        form = await self.login(await self.begin())
        invalid = await self.http.post(
            "/oauth/approve",
            data={**form, "csrf_token": "invalid", "decision": "approve"},
            headers={"Origin": test_oauth.ORIGIN},
        )
        self.assertEqual(invalid.status_code, 403)
        self.assertFalse(self.provider.code_store.codes)
        response = await self.http.post(
            "/oauth/approve",
            data={**form, "decision": "deny"},
            headers={"Origin": test_oauth.ORIGIN},
        )
        self.assertEqual(response.status_code, 303)
        query = parse_qs(urlsplit(response.headers["location"]).query)
        self.assertEqual(query["error"], ["access_denied"])
        self.assertNotIn("code", query)
        self.assertFalse(self.provider.code_store.codes)

    async def test_public_stylesheet_on_combined_app_and_strict_api_csp(self):
        app = create_remote_app(provider=self.provider, session_secret="page-test-secret" * 3)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=test_oauth.ORIGIN
        ) as client:
            logo = await client.get("/oauth/static/relay-light.png")
            self.assertEqual(logo.status_code, 200)
            self.assertEqual(logo.headers["content-type"], "image/png")
            from pathlib import Path

            original = (
                Path(__file__).resolve().parents[3] / "frontend/public/brand/relay/relay-light.png"
            )
            self.assertEqual(logo.content, original.read_bytes())
            css = await client.get("/oauth/static/relay.css")
            self.assertEqual(css.status_code, 200)
            self.assertTrue(css.headers["content-type"].startswith("text/css"))
            self.assertEqual(css.headers["x-content-type-options"], "nosniff")
            self.assertIn("prefers-reduced-motion", css.text)
            self.assertIn(":focus-visible", css.text)
            self.assertNotIn("@import", css.text)
            self.assertNotIn("url(", css.text)
            self.assertEqual((await client.head("/oauth/static/relay.css")).status_code, 200)
            for path, status in (("/.well-known/oauth-authorization-server", 200), ("/mcp", 401)):
                response = await client.get(path)
                self.assertEqual(response.status_code, status)
                self.assertEqual(
                    response.headers["content-security-policy"],
                    "default-src 'none'; frame-ancestors 'none'",
                )

    async def test_error_html_is_not_cached(self):
        response = await self.http.get("/oauth/consent")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["content-security-policy"], HTML_CSP)
        self.assertEqual(response.headers["cache-control"], "no-store")
