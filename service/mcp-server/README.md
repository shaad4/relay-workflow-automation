# Relay MCP — Phase 2, Batch 2

Two entry points share the same 16 tool definitions and input/output schemas:

- **Codex stdio:** `./start_mcp.sh` still runs `server.py`, using the existing
  single-account `RelaySession`. Its environment and transport are unchanged.
- **Local Streamable HTTP:** `remote_server.py` combines the Batch 1 OAuth routes
  and `/mcp` in one ASGI application with one provider and set of in-memory stores.
  It never imports `server.py` or constructs its single-account session.

## Local startup

From `service/mcp-server`, use the existing `.venv` with `requirements.txt` installed.
Set these environment values without committing secrets:

```sh
export RELAY_API_URL=https://relay.shaad.site/api/relay
export MCP_PUBLIC_ORIGIN=http://127.0.0.1:8001
# Set MCP_SESSION_SECRET to a cryptographically random value of at least 32 characters.
.venv/bin/python remote_server.py
```

The runner binds only to **127.0.0.1:8001**, disables access logs and proxy-header
trust, and uses one process. The app also rejects non-loopback peers and mismatched
Host/Origin headers. Do not tunnel, reverse-proxy, run multiple workers, or expose it
publicly. No deployment is included.

Endpoint and OAuth audience: **http://127.0.0.1:8001/mcp**.

Discovery endpoints:

- `/.well-known/oauth-authorization-server`
- `/.well-known/oauth-protected-resource/mcp`

Register using `/register`, authorize using `/authorize`, log in and approve in the
browser, exchange the code at `/token`, then send `Authorization: Bearer <OAuth access
token>` on **every** MCP request. Streamable HTTP uses stateless sessions and JSON
responses; initialize normally and send the SDK's required protocol/Accept headers.
No unauthenticated tool discovery or tool calls are allowed. Revocation is `/revoke`.
See [OAuth details](oauth/README.md) for PKCE, redirect, consent, refresh and storage rules.

## Server icon

The HTTP MCP server advertises `oauth/static/relay-icon-black.png` in its server
info `icons` metadata. Its URL is built from `MCP_PUBLIC_ORIGIN` plus
`/oauth/static/relay-icon-black.png`; GET and HEAD serve the PNG without an OAuth
token. The metadata declares the supplied image's actual dimensions, 1308×1202.
The existing Dockerfile includes the asset through `COPY oauth/ ./oauth/`.

Rebuild and redeploy the MCP server, then reconnect the client to refresh its
server metadata. Display is controlled by the client; advertising an icon does
not guarantee Claude will display it for a custom connector.
See the [Python SDK icon documentation](https://py.sdk.modelcontextprotocol.io/servers/media/#icons).

## Explicit K3s deployment mode (configuration only)

Local mode remains the default. Container mode must be explicitly selected:

```sh
export MCP_DEPLOYMENT_MODE=k3s
export MCP_PUBLIC_ORIGIN=https://mcp.relay.shaad.site
export MCP_PORT=8001
# Set MCP_TRUSTED_PROXY_IPS to the actual ingress peer IPs or narrowly scoped CIDRs,
# comma-separated. It has no default; do not use the whole pod/node network.
# Supply MCP_SESSION_SECRET and RELAY_API_URL through deployment secrets/config.
.venv/bin/python remote_server.py
```

This runner binds `0.0.0.0:$MCP_PORT` with **one Uvicorn worker**. Keep **one K3s
replica**; replicas cannot share the in-memory OAuth state. No manifests have been
changed and nothing has been deployed. This section supersedes the local-only bind
instructions above only when `MCP_DEPLOYMENT_MODE=k3s` is explicitly set.

The public origin must be exactly `https://mcp.relay.shaad.site` (an optional trailing
slash is normalized). The OAuth issuer/endpoints, secure browser cookies, allowed
Host/Origin, and resource audience use this configured origin, never forwarded host
headers. The protected endpoint is `https://mcp.relay.shaad.site/mcp`; both discovery
endpoints and OAuth routes remain available.

In K3s mode, the loopback peer gate is replaced with an explicit ingress peer
allowlist. The **original socket peer** must match `MCP_TRUSTED_PROXY_IPS` before
Uvicorn's installed proxy middleware processes `X-Forwarded-For` and
`X-Forwarded-Proto`. Wildcards, empty lists and all-address CIDRs are rejected.
`Forwarded` and `X-Forwarded-Host` do not override the configured identity or Host
checks. The outer Uvicorn server keeps `proxy_headers=False` to avoid interpreting
headers before the peer check; use this runner rather than an independently
configured Uvicorn CLI. `FORWARDED_ALLOW_IPS` is not used.

Traefik must terminate HTTPS, preserve the public Host header, and overwrite/sanitize
forwarded headers from external callers. Configure the narrowest actual source
addresses seen by the pod, accounting for cluster NAT. Source-IP trust is not
cryptographic: a compromised allowed ingress or an overly broad CIDR defeats this
boundary. A future deployment also needs ingress-only network policy, TLS/secrets,
and operational validation. OAuth, audience, CSRF, and per-tool permission checks
remain enabled regardless of forwarded headers. Existing memory, rate-limit and
restart limitations still apply; this is deployment-mode support, not production
readiness or authorization to expose the service.

## Scopes

Register and request the desired space-separated scopes explicitly. The default
registration scope is `relay:read`; omitted authorization scope grants read only if
registered. The previous generic `relay` scope is no longer accepted for registration
or tool authorization. Scope reduction during refresh is supported; escalation is not.

| Scope | Tools |
| --- | --- |
| `relay:read` | `relay_list_workflows`, `relay_list_executions`, `relay_get_execution_steps` |
| `relay:write` | `relay_create_workflow`, `relay_add_node`, `relay_update_node`, `relay_add_edge`, `relay_validate_workflow`, `relay_create_complete_workflow` |
| `relay:execute` | `relay_publish_workflow`, `relay_deactivate_workflow`, `relay_run_workflow` |
| `relay:delete` | `relay_delete_workflow`, `relay_delete_node`, `relay_delete_edge` |

`relay_hello` requires a valid OAuth token but no additional scope. Discovery lists
all tools so clients can discover their contracts; permission checks run on every
call. Scope denial is an MCP tool error; missing/invalid/expired/revoked/wrong-audience
bearer credentials produce HTTP 401 with protected-resource discovery information.

## Per-user authorization

SDK 2.3.0 `MCPServer.streamable_http_app` installs the supported bearer authentication
and request-local auth context using `ProviderTokenVerifier` and `AuthSettings` with
`validate_token_resource=True`. A root mount preserves these SDK middleware layers;
the combined app owns the HTTP session manager's lifespan. Custom Batch 1 OAuth
routes remain authoritative, including PKCE/resource/redirect guards.

For each tool invocation:

1. Read the SDK's authenticated token context and re-check it in the shared provider.
2. Check the exact required tool scope, then resolve its grant to the server-side
   `UserRelaySession`. The user ID must match the token subject. Login records the
   verified user and workspace from Relay; neither comes from tool arguments.
   Top-level user/workspace identity overrides are rejected before SDK validation.
3. Construct a fresh `httpx.AsyncClient`, `DelegatedRequestSession`, and `RelayClient`
   for that invocation. Clients/cookie jars are never shared between users or calls.
4. Before each workflow/history REST request, revalidate `/auth/me`, compare both
   user and workspace with the approved identity, and check OAuth liveness again.
   Relay's existing APIs enforce their own authenticated workspace/resource access.
5. Close the HTTP client after the tool returns. Scrub credential fields and known
   credential values from returned data; failures use safe messages without upstream
   response bodies, URLs or credentials. Resource identifiers cannot inject path/query
   structure into Relay API requests.

Relay sessions are **revalidated, not silently refreshed** in this batch. An expired
or revoked session fails securely and requires a fresh OAuth authorization/login;
there is no fallback account. The existing Auth Service `/auth/me` checks session
revocation for session-bound access tokens. This implementation relies on that
existing service behavior and does not decode or sign Relay JWTs.

## Validation

From repository root:

```sh
service/mcp-server/.venv/bin/python -m unittest discover -s service/mcp-server/tests -v
```

All Relay HTTP traffic in tests is mocked. Tests cover OAuth regressions both alone
and in the combined app, initialization/discovery, all 16 tools against all four
scopes, credential expiry/revocation/audience, consent denial, concurrent users,
workspace denial, changed/expired/revoked Relay identity, cookie isolation, response
redaction, uncertain mutation handling, path injection and local-origin restrictions.
The stdio subprocess check initializes the existing entry point, compares tool
contracts with shared registration, and calls only `relay_hello` (no live Relay API).
Some sandboxes block the SDK's subprocess transport; run the suite in a normal local
shell if that specific probe times out.

## Remaining limitations

- All OAuth records and delegated credentials are in process memory. Restart loses
  them; multiple workers are unsupported. Expiry cleanup is opportunistic. There
  are no quotas, production rate limits, persistent audit facilities or encrypted
  credential storage. Do not expose publicly.
- HTTP is allowed only for the local demonstration; browser session cookies use
  HttpOnly/SameSite but cannot use Secure on HTTP. Cross-origin browser MCP clients
  are not enabled. The supported runner disables forwarded-header trust.
- OAuth rotation does not extend the one-hour grant. A still-valid OAuth token may
  outlive the underlying Relay access token, in which case tools fail until login.
  Old/legacy Relay JWTs without a server session ID retain the Auth Service's own
  revocation limitations; MCP cannot invent stronger upstream revocation guarantees.
- Scope checks narrow access; they never grant more than Relay permits. Workspace
  isolation ultimately relies on Relay's API authorization. Tests simulate its
  denials; they do not substitute for an end-to-end production permission audit.
- Revocation prevents subsequent requests; it cannot cancel a mutation already
  accepted by Relay. No workflow mutation is automatically retried. Complete workflow
  creation remains a sequence of operations and may leave an incomplete draft after
  a failure; inspect the outcome before retrying manually.
- Redaction protects authentication credentials, not all sensitive user-created
  workflow/execution data. Authorized read tools still return Relay's permitted data.

Batch 2 stops here: no public deployment, frontend/schema/service changes, or K3s work.
