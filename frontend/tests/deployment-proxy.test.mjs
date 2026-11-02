import test from "node:test";
import assert from "node:assert/strict";
import {
  proxyConfig,
  proxyCookie,
  proxyLocation,
  proxyRequest,
  gatewayReady,
} from "../src/lib/server/apiProxy.js";

const env = {
  NODE_ENV: "production",
  API_GATEWAY_URL: "http://api-gateway:8000",
  FRONTEND_URL: "https://relay.example.com",
};
const request = (path, init = {}) =>
  new Request(`https://relay.example.com/api/relay${path}`, init);

test("runtime configuration keeps server DNS private and accepts dev defaults", () => {
  assert.equal(proxyConfig({}).gateway, "http://127.0.0.1:8001");
  assert.equal(proxyConfig(env).gateway, "http://api-gateway:8000");
  assert.equal(
    proxyConfig({ ...env, API_GATEWAY_URL: "https://gateway.example.com" })
      .gateway,
    "https://gateway.example.com",
  );
  assert.throws(() => proxyConfig({ NODE_ENV: "production" }), /required/);
  for (const value of [
    "not-a-url",
    "file:///etc/passwd",
    "http://user:private-password@host",
    "http://host/path",
    "http://host?secret=value",
  ]) {
    assert.throws(
      () => proxyConfig({ ...env, API_GATEWAY_URL: value }),
      (error) => {
        assert.doesNotMatch(error.message, /private-password|secret=value/);
        return true;
      },
    );
  }
  for (const value of ["0", "NaN", "1.5", "601"]) {
    assert.throws(
      () => proxyConfig({ ...env, API_PROXY_TIMEOUT_SECONDS: value }),
      /limits/,
    );
  }
});

test("same-origin client URLs require no build environment and produce absolute webhooks", async () => {
  const previous = process.env.NEXT_PUBLIC_AUTH_API_URL;
  const previousWindow = globalThis.window;
  delete process.env.NEXT_PUBLIC_AUTH_API_URL;
  const { apiUrl } = await import(`../src/lib/api.js?deployment=${Date.now()}`);
  try {
    assert.equal(apiUrl("/auth/refresh"), "/api/relay/auth/refresh");
    globalThis.window = { location: { origin: "https://relay.example.com" } };
    assert.equal(
      apiUrl("/hooks/token", { absolute: true }),
      "https://relay.example.com/api/relay/hooks/token",
    );
  } finally {
    if (previous === undefined) delete process.env.NEXT_PUBLIC_AUTH_API_URL;
    else process.env.NEXT_PUBLIC_AUTH_API_URL = previous;
    globalThis.window = previousWindow;
  }
});

test("proxy keeps methods, query, encoded paths, multipart body, and authentication", async () => {
  let call;
  const result = await proxyRequest(
    request("/knowledge-bases/id/documents/?q=a%20b", {
      method: "POST",
      headers: {
        origin: env.FRONTEND_URL,
        cookie: "relay_access_token=test-cookie",
        "content-type": "multipart/form-data; boundary=test",
        "x-forwarded-host": "attacker.example",
        connection: "x-remove",
        "x-remove": "private",
      },
      body: "--test\r\nsynthetic document\r\n--test--",
    }),
    {
      env,
      fetchImpl: async (url, options) => {
        call = { url, options };
        return Response.json({ id: "document" }, { status: 201 });
      },
    },
  );
  assert.equal(result.status, 201);
  assert.equal(
    call.url.href,
    "http://api-gateway:8000/knowledge-bases/id/documents/?q=a%20b",
  );
  assert.equal(call.options.method, "POST");
  assert.equal(
    call.options.headers.get("cookie"),
    "relay_access_token=test-cookie",
  );
  assert.equal(
    call.options.headers.get("content-type"),
    "multipart/form-data; boundary=test",
  );
  assert.equal(call.options.headers.get("x-forwarded-host"), null);
  assert.equal(call.options.headers.get("x-remove"), null);
  assert.equal(call.options.redirect, "manual");
  assert.match(call.options.body.toString(), /synthetic document/);
  assert.equal(result.headers.get("cache-control"), "no-store");
});

test("path and query cannot select an arbitrary upstream host", async () => {
  for (const path of [
    "//evil.example/path",
    "/https:%2F%2Fevil.example/",
    "/auth?url=https://evil.example",
  ]) {
    await proxyRequest(request(path), {
      env,
      fetchImpl: async (url) => {
        assert.equal(url.origin, env.API_GATEWAY_URL);
        return Response.json({ ok: true });
      },
    });
  }
});

test("cross-origin cookie mutations and login CSRF are rejected before contacting gateway", async () => {
  for (const headers of [
    { origin: "https://evil.example", cookie: "relay_access_token=test" },
    { origin: "https://evil.example" },
    { "sec-fetch-site": "cross-site" },
    { cookie: "relay_access_token=test" },
    { cookie: "relay_access_token=test", referer: "https://evil.example/page" },
  ]) {
    const response = await proxyRequest(
      request("/auth/login", { method: "POST", headers }),
      {
        env,
        fetchImpl: () => {
          throw new Error("must not call");
        },
      },
    );
    assert.equal(response.status, 403);
  }
});

test("same-origin mutations and non-browser webhooks remain usable", async () => {
  for (const headers of [
    { origin: env.FRONTEND_URL, cookie: "relay_access_token=test" },
    {
      referer: `${env.FRONTEND_URL}/dashboard`,
      cookie: "relay_access_token=test",
    },
    { "x-webhook-signature": "synthetic" },
  ]) {
    const response = await proxyRequest(
      request("/hooks/token", { method: "POST", headers, body: "{}" }),
      { env, fetchImpl: async () => new Response(null, { status: 204 }) },
    );
    assert.equal(response.status, 204);
  }
});

test("refresh and OAuth cookie paths are rewritten without combining Set-Cookie headers", async () => {
  const upstreamHeaders = new Headers();
  upstreamHeaders.append(
    "set-cookie",
    "relay_access_token=a; Path=/; HttpOnly; Secure; SameSite=Lax",
  );
  upstreamHeaders.append(
    "set-cookie",
    "relay_refresh_token=b; Domain=api.example.com; Path=/auth; HttpOnly; Secure",
  );
  upstreamHeaders.append(
    "set-cookie",
    "google_oauth_state=c; Path=/auth/google; Max-Age=600; HttpOnly; Secure",
  );
  const response = await proxyRequest(request("/auth/login"), {
    env,
    fetchImpl: async () => new Response("{}", { headers: upstreamHeaders }),
  });
  const cookies = response.headers.getSetCookie();
  assert.equal(cookies.length, 3);
  assert.match(cookies[0], /Path=\//);
  assert.match(cookies[1], /Path=\/api\/relay\/auth;/);
  assert.match(cookies[2], /Path=\/api\/relay\/auth\/google;/);
  assert.doesNotMatch(cookies.join(" "), /Domain=/);
  assert.equal(
    proxyCookie("relay_refresh_token=; Path=/auth; Max-Age=0"),
    "relay_refresh_token=; Path=/api/relay/auth; Max-Age=0",
  );
});

test("redirects stay in proxy for backend paths and preserve external OAuth locations", async () => {
  const target = new URL("http://api-gateway:8000/workflows");
  assert.equal(proxyLocation("/workflows/", target), "/api/relay/workflows/");
  assert.equal(
    proxyLocation("http://api-gateway:8000/workflows/?q=x", target),
    "/api/relay/workflows/?q=x",
  );
  assert.equal(
    proxyLocation(
      "https://accounts.google.com/o/oauth2/auth?state=test",
      target,
    ),
    "https://accounts.google.com/o/oauth2/auth?state=test",
  );
  assert.equal(proxyLocation("javascript:alert(1)", target), null);
  const response = await proxyRequest(request("/auth/google"), {
    env,
    fetchImpl: async () =>
      new Response(null, {
        status: 307,
        headers: {
          location: "https://accounts.google.com/o/oauth2/auth?state=test",
        },
      }),
  });
  assert.equal(response.status, 307);
  assert.equal(
    response.headers.get("location"),
    "https://accounts.google.com/o/oauth2/auth?state=test",
  );
});

test("oversize bodies are rejected both with and without Content-Length", async () => {
  for (const headers of [{}, { "content-length": "100" }]) {
    const response = await proxyRequest(
      request("/hooks/token", { method: "POST", headers, body: "large" }),
      {
        env: { ...env, API_PROXY_MAX_BODY_BYTES: "4" },
        fetchImpl: () => {
          throw new Error("must not call");
        },
      },
    );
    assert.equal(response.status, 413);
  }
});

test("network/config errors expose neither upstream addresses nor credentials", async () => {
  const response = await proxyRequest(request("/auth/me"), {
    env,
    fetchImpl: () => {
      throw new Error("http://private:secret@internal-host");
    },
  });
  assert.equal(response.status, 502);
  assert.doesNotMatch(await response.text(), /private|secret|internal-host/);
  const invalid = await proxyRequest(request("/auth/me"), {
    env: { ...env, API_GATEWAY_URL: "http://private:secret@internal-host" },
  });
  assert.equal(invalid.status, 503);
  assert.doesNotMatch(await invalid.text(), /private|secret|internal-host/);
});

test("readiness checks the gateway at runtime and fails closed without config", async () => {
  assert.equal(
    (
      await gatewayReady({
        env,
        fetchImpl: async (url) => {
          assert.equal(url, "http://api-gateway:8000/ready");
          return Response.json({ ready: true });
        },
      })
    ).status,
    200,
  );
  assert.equal(
    (
      await gatewayReady({
        env,
        fetchImpl: async () => new Response(null, { status: 503 }),
      })
    ).status,
    503,
  );
  assert.equal(
    (await gatewayReady({ env: { NODE_ENV: "production" } })).status,
    503,
  );
});

test("body reception shares the proxy deadline and cancels a stalled stream", async () => {
  let cancelled = false;
  let contactedGateway = false;
  const body = new ReadableStream({
    pull() {
      return new Promise(() => {});
    },
    cancel() {
      cancelled = true;
      return new Promise(() => {});
    },
  });
  const response = await proxyRequest(
    request("/hooks/token", {
      method: "POST",
      body,
      duplex: "half",
    }),
    {
      env: { ...env, API_PROXY_TIMEOUT_SECONDS: "1" },
      fetchImpl: async () => {
        contactedGateway = true;
        return Response.json({ ok: true });
      },
    },
  );
  assert.equal(response.status, 408);
  assert.equal(cancelled, true);
  assert.equal(contactedGateway, false);
});

test("caller abort cancels a pending body read before any upstream request", async () => {
  const controller = new AbortController();
  let cancelled = false;
  let contactedGateway = false;
  let startReading;
  const reading = new Promise((resolve) => {
    startReading = resolve;
  });
  const body = new ReadableStream({
    pull() {
      startReading();
      return new Promise(() => {});
    },
    cancel() {
      cancelled = true;
    },
  });
  const responsePromise = proxyRequest(
    request("/hooks/token", {
      method: "POST",
      body,
      duplex: "half",
      signal: controller.signal,
    }),
    {
      env,
      fetchImpl: async () => {
        contactedGateway = true;
        return Response.json({ ok: true });
      },
    },
  );
  await reading;
  controller.abort();
  assert.equal((await responsePromise).status, 400);
  assert.equal(cancelled, true);
  assert.equal(contactedGateway, false);
});

test("the same deadline signal is used after body reception", async () => {
  const controller = new AbortController();
  let forwardedSignal;
  const response = await proxyRequest(
    request("/hooks/token", {
      method: "POST",
      body: "{}",
      signal: controller.signal,
    }),
    {
      env,
      fetchImpl: async (_url, { signal }) => {
        forwardedSignal = signal;
        assert.equal(signal.aborted, false);
        controller.abort();
        assert.equal(signal.aborted, true);
        throw signal.reason;
      },
    },
  );
  assert.ok(forwardedSignal);
  assert.equal(response.status, 502);
});

test("an already aborted request releases its unread body", async () => {
  const controller = new AbortController();
  controller.abort();
  let cancelled = false;
  const body = new ReadableStream({
    pull() {
      return new Promise(() => {});
    },
    cancel() {
      cancelled = true;
    },
  });
  const response = await proxyRequest(
    request("/hooks/token", {
      method: "POST",
      body,
      duplex: "half",
      signal: controller.signal,
    }),
    {
      env,
      fetchImpl: () => {
        throw new Error("must not call");
      },
    },
  );
  assert.equal(response.status, 400);
  assert.equal(cancelled, true);
});
