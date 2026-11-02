// Local synthetic gateway only: no databases, credentials or external providers.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { cp, access } from "node:fs/promises";
import http from "node:http";
import { once } from "node:events";
import { setTimeout as delay } from "node:timers/promises";

await access(".next/standalone/server.js");
await cp("public", ".next/standalone/public", { recursive: true });
await cp(".next/static", ".next/standalone/.next/static", { recursive: true });
const gateway = http.createServer(async (req, res) => {
  if (req.url === "/auth/login") {
    res.setHeader("Set-Cookie", [
      "relay_access_token=synthetic; Path=/; HttpOnly; SameSite=Lax",
      "relay_refresh_token=synthetic; Path=/auth; HttpOnly; SameSite=Lax",
    ]);
    res.setHeader("Content-Type", "application/json");
    res.end('{"token_type":"bearer"}');
  } else if (req.url === "/auth/google") {
    res.writeHead(307, {
      Location: "https://accounts.google.com/o/oauth2/auth?state=synthetic",
    });
    res.end();
  } else if (req.url === "/auth/refresh") {
    assert.match(req.headers.cookie || "", /relay_refresh_token=synthetic/);
    res.setHeader("Content-Type", "application/json");
    res.end('{"token_type":"bearer"}');
  } else {
    res.setHeader("Content-Type", "application/json");
    res.end('{"status":"ready"}');
  }
});
gateway.listen(0, "127.0.0.1");
await once(gateway, "listening");
const portReservation = http.createServer();
portReservation.listen(0, "127.0.0.1");
await once(portReservation, "listening");
const port = portReservation.address().port;
await new Promise((resolve) => portReservation.close(resolve));
const origin = `http://127.0.0.1:${port}`;
const server = spawn(process.execPath, [".next/standalone/server.js"], {
  env: {
    ...process.env,
    NODE_ENV: "production",
    HOSTNAME: "127.0.0.1",
    PORT: String(port),
    API_GATEWAY_URL: `http://127.0.0.1:${gateway.address().port}`,
    FRONTEND_URL: origin,
  },
  stdio: "ignore",
});
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      ready = (await fetch(`${origin}/health`)).ok;
    } catch {
      /* process is starting */
    }
    if (ready) break;
    if (server.exitCode !== null)
      throw new Error("Standalone server exited before health check");
    await delay(100);
  }
  assert.ok(ready, "standalone server started within 10 seconds");
  assert.equal((await fetch(`${origin}/ready`)).status, 200);
  assert.equal((await fetch(`${origin}/login`)).status, 200);
  // Legal pages must render fully without cookies, authentication, or a workspace.
  for (const [path, title] of [
    ["/privacy", "Privacy Policy"],
    ["/terms", "Terms of Service"],
  ]) {
    const response = await fetch(`${origin}${path}`, { redirect: "manual" });
    assert.equal(response.status, 200, `${path} is public`);
    const html = await response.text();
    assert.ok(html.includes(title), `${path} includes its policy content`);
    assert.ok(
      html.includes('href="/privacy"') && html.includes('href="/terms"'),
    );
    assert.ok(html.includes("mailto:groveworkspace@gmail.com"));
    assert.ok(html.includes(`https://relay.shaad.site${path}`));
  }
  const login = await fetch(`${origin}/api/relay/auth/login`, {
    method: "POST",
    headers: { origin, "content-type": "application/json" },
    body: '{"email":"synthetic@example.test","password":"test-only"}',
  });
  assert.equal(login.status, 200);
  assert.equal(login.headers.getSetCookie().length, 2);
  assert.match(login.headers.getSetCookie()[1], /Path=\/api\/relay\/auth/);
  const refresh = await fetch(`${origin}/api/relay/auth/refresh`, {
    method: "POST",
    headers: { origin, cookie: "relay_refresh_token=synthetic" },
  });
  assert.equal(refresh.status, 200);
  const denied = await fetch(`${origin}/api/relay/auth/refresh`, {
    method: "POST",
    headers: {
      origin: "https://untrusted.example",
      cookie: "relay_refresh_token=synthetic",
    },
  });
  assert.equal(denied.status, 403);
  const oauth = await fetch(`${origin}/api/relay/auth/google`, {
    redirect: "manual",
  });
  assert.equal(oauth.status, 307);
  assert.match(
    oauth.headers.get("location"),
    /^https:\/\/accounts.google.com\//,
  );
  await new Promise((resolve) => gateway.close(resolve));
  assert.equal((await fetch(`${origin}/ready`)).status, 503);
  assert.equal((await fetch(`${origin}/health`)).status, 200);
  assert.equal((await fetch(`${origin}/api/relay/auth/me`)).status, 502);
  process.stdout.write(
    "Standalone smoke passed: runtime upstream, login page, health/readiness, cookies, refresh, CSRF, OAuth redirect, dependency failure.\n",
  );
} finally {
  gateway.closeAllConnections();
  gateway.close();
  server.kill("SIGTERM");
  await once(server, "exit");
}
