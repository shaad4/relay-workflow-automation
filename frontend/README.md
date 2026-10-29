# Relay frontend

The Next.js dashboard and workflow builder use the same production image under
Docker Compose and Kubernetes. No redesign or build-time secret injection is
needed. See [deployment guide](../deploy/README.md) for the complete platform.

## Local development

```bash
npm ci
cp .env.example .env.local
# Start the backend with the root Compose instructions, then:
npm run dev
```

Open `http://localhost:3000`. The browser calls `/api/relay/*` on this origin;
Next forwards requests to `API_GATEWAY_URL` (default `http://127.0.0.1:8001`
outside containers). Never set the upstream to the frontend itself.

## Runtime configuration

| Setting                     | Scope                   | Requirement                                                                                                                      |
| --------------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `API_GATEWAY_URL`           | Server only, runtime    | Gateway HTTP(S) origin, e.g. `http://api-gateway:8000`; required with `NODE_ENV=production`                                      |
| `FRONTEND_URL`              | Server only, runtime    | Exact browser origin; required in production, e.g. `https://relay.example.com`; must match the gateway's origin allowlist        |
| `API_PROXY_TIMEOUT_SECONDS` | Server only, runtime    | 120 by default; integer 1–600, covering body reception, upstream and streamed responses                                          |
| `API_PROXY_MAX_BODY_BYTES`  | Server only, runtime    | 12 MiB by default (10 MiB RAG document plus multipart overhead); integer up to 100 MiB; does not change the backend's file limit |
| `NEXT_PUBLIC_AUTH_API_URL`  | Browser, **build time** | Optional legacy direct gateway mode only. Leave unset for portable images. Never put secrets here.                               |

`API_GATEWAY_URL` accepts an origin only, with no embedded credentials, path,
query or fragment. It is not sent to the browser. Changing runtime settings
requires restarting the container, not rebuilding it. Invalid production
configuration fails `/ready` and proxy requests without disclosing values.
The JS application uses client-side API calls; future Server Components should
call the private gateway server-side, not assume relative URLs work in Node.

The legacy direct gateway mode is retained for manual `npm run build` deployments
using `NEXT_PUBLIC_AUTH_API_URL`; it is intentionally not a Docker build argument.
It requires a rebuild to change the public API URL
and a gateway CORS allowlist matching `FRONTEND_URL`. Use HTTPS, secure cookies
and same-site frontend/API domains. Cross-site cookies need a separate threat
review and must not be enabled just to bypass CORS failures.

## Container

```bash
docker build -t relay/frontend:dev frontend # run from repository root
```

The Dockerfile uses the checked-in npm lockfile, a separate build stage, Next's
[standalone output](https://nextjs.org/docs/app/api-reference/config/next-config-js/output),
and a non-root UID/GID `10001`. Node handles termination directly as PID 1.
The runtime listens on port `3000`; provide `API_GATEWAY_URL` and `FRONTEND_URL`
in Compose/Kubernetes. No database or AI credentials belong in this container.
Only `/tmp` and `/app/.next/cache` need writable mounts with a read-only root.
Google Geist fonts are fetched at build time by the existing `next/font` setup;
build runners need access to the font service, while the runtime serves them
locally. Multi-architecture image builds still require validation on both
`linux/amd64` and `linux/arm64`.

- `GET /health`: local process health, independent of the gateway.
- `GET /ready`: runtime configuration and gateway `/ready` check (3s deadline).
- Health endpoints contain no credentials or upstream error details.

## HTTPS, cookies, OAuth, and webhooks

Terminate HTTPS at the reverse proxy/ingress. Keep the gateway private unless a
separate public API is deliberately needed. Configure the auth service with
`COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax` in production; browser requests use
`credentials: include`. The frontend proxy preserves separate `Set-Cookie`
headers, makes cookies host-only, and maps refresh/OAuth cookie paths from
`/auth...` to `/api/relay/auth...`. Existing direct-API sessions are not copied
between domains or paths; users may need to sign in again after switching modes.

For same-origin deployment, configure Google console callbacks and matching
backend settings explicitly:

```text
GOOGLE_REDIRECT_URI=https://relay.example.com/api/relay/auth/google/callback
GOOGLE_GMAIL_REDIRECT_URI=https://relay.example.com/api/relay/connections/gmail/oauth/callback
```

These are provider/backend callbacks, not the UI's
`/auth/google/callback` page. Backend redirects to that page remain unchanged.
Google client secrets stay in the appropriate backend service. Existing keys do
not need rotation solely because of this refactor.

The proxy rejects untrusted browser mutation origins, strips spoofed forwarding
headers, rejects oversized bodies, never lets the caller choose an upstream
host, never follows gateway redirects, and never caches private responses.
Cookie-authenticated non-browser requests must supply the configured `Origin`
or a matching `Referer`. Server webhook clients without cookies/Origin remain
supported; the backend continues to enforce webhook tokens/signatures.
Webhook URLs shown by the UI are absolute public URLs including `/api/relay`.

No WebSocket client exists in the current frontend. This route handler is an
HTTP proxy, **not** a WebSocket upgrade tunnel. If WebSockets are added later,
route those separately at the ingress/reverse proxy and verify authentication.
At the edge, configure appropriate request timeouts/body limits and request
rate limits; the in-process proxy is not a substitute for those controls.

## Verification

```bash
npm test
npm run lint
npm run format:check
npm run build
npm run test:standalone
npm audit --audit-level=high
```

`test:standalone` requires a completed build. It starts a temporary local
synthetic gateway and standalone server, verifies runtime configuration,
login-page serving, cookies/refresh, CSRF, OAuth redirects, health/readiness and
dependency failures, then stops both. It never invokes providers or databases.
The optional dashboard browser regression needs `RELAY_DASHBOARD_URL`,
`RELAY_PLAYWRIGHT_MODULE`, and a Chromium path in `RELAY_CHROME`; it mocks API
traffic. Authentication email delivery, real OAuth, BYOK calls, document uploads
and end-to-end executions still require a separately authorized staging smoke
test before production deployment.
