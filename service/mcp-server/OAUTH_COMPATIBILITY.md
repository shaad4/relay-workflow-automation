# MCP OAuth compatibility audits

## Dynamic registration scope negotiation

**Current revision: regression tests added/updated but NOT RUN, as requested.**
Earlier passing test counts below apply to the earlier revisions only. No deployment,
live registration changes, or workflow calls were performed for this revision.

### Precise failure

The reported JSON is emitted by the original intersection check in
`oauth/app.py:100-102`, before the SDK authorization handler. For the exact supplied
request `relay:read relay:write relay:delete relay:execute`, every scope is supported.
The failing condition is therefore at least one scope missing from the registered
client's `scope`, not missing support in discovery. After this change, that specific
condition is at `oauth/app.py:106-111`; unsupported/malformed scope names are separately
rejected at `oauth/app.py:104-105` with a different static diagnostic.

The old DCR configuration (`default_scopes=["relay:read"]`) caused clients omitting
the optional registration scope field to be stored as read-only. The SDK registration
handler applies that default, and `oauth/provider.py:80` stores the full registration
unchanged. Explicit requests for all four valid scopes were already accepted and
stored; there was no truncation to read-only in that path. Discovery advertises the
same `SCOPES` list accepted by registration and authorization.

The exact original ChatGPT registration request and in-memory record were not
available. The supplied error establishes the registration mismatch for the exact
scope string above, but does not establish whether ChatGPT omitted registration
scope or explicitly requested a restricted list. No raw OAuth URLs, secrets, tokens,
or live registry contents were collected. Malformed separators would instead fall
under the new unsupported-scope diagnostic.

### Minimal change and security boundaries

`oauth/app.py:57-62` now defaults only **new registrations with omitted scope** to
the supported scope list. This is a client eligibility list, not an access grant.
[RFC 7591 section 2](https://www.rfc-editor.org/rfc/rfc7591.html#section-2) permits
server-selected registration defaults when scope is omitted. Explicit restricted
registrations and existing records are not expanded.

`/authorize` still enforces both supported and registered scopes, and now explains
which condition failed without echoing request data. `oauth/provider.py:85-88` still
defaults omitted authorization scope to read-only. Login, explicit approval, PKCE,
redirect matching, audience checks, per-tool checks and token issuance are unchanged.
Refresh cannot grant scopes beyond the existing grant. No client-name exceptions or
workflow/engine changes were introduced; Claude uses the same existing rules.

### Reconnection and deployment

ChatGPT performs DCR once per MCP connection and reuses that client, so reauthorization
alone does not replace an old read-only registration.
[OpenAI authentication](https://developers.openai.com/plugins/build/auth)

1. Rebuild and redeploy only MCP using the commands below. Keep the existing single
   replica/worker and `Recreate` strategy.
2. Remove and recreate ChatGPT's custom MCP server connection to trigger fresh DCR,
   rather than only disconnecting/reconnecting account authorization. Use endpoint
   `https://mcp.relay.shaad.site/mcp`, OAuth, and automatic client registration.
3. If configuring explicit registration scopes, include the scopes ChatGPT will
   request. Its observed four-scope request needs all four registered. Omitting
   registration scopes now also supports that request. For just listing/running,
   configure both requests as `relay:read relay:execute` if the client allows it.
4. Review Relay's consent page. All four requested permissions must be shown when
   all four are requested. Approve only if those operations are wanted; declining
   must issue no code/token. No need to supply a pre-created client secret for DCR.
5. If the client was already registered for all requested scopes, fresh authorization
   and consent suffice; refresh alone never expands an existing read-only grant.

From the repository root (manual commands, not executed):

```sh
MCP_IMAGE="relay-mcp:dcr-scopes-$(date -u +%Y%m%d%H%M%S)"
docker build -t "$MCP_IMAGE" service/mcp-server
docker save -o /tmp/relay-mcp-dcr-scopes.tar "$MCP_IMAGE"
sudo k3s ctr -n k8s.io images import /tmp/relay-mcp-dcr-scopes.tar
sudo k3s kubectl -n relay set image deployment/relay-mcp relay-mcp="$MCP_IMAGE"
sudo k3s kubectl -n relay rollout status deployment/relay-mcp --timeout=300s
```

Import on every eligible node first. No frontend rebuild is needed. The existing
in-memory OAuth storage loses registrations/tokens on restart, including Claude's;
recreate Claude's connection after the final restart as needed. This is existing
deployment behavior, not a change to Claude's scope handling.

### Added regression coverage (not executed)

`tests/test_remote.py` covers omitted and explicit four-scope DCR for both synthetic
ChatGPT and Claude clients; stored/returned scopes; all four consent labels; no token
before login/approval; denial; exact code/token scopes; refresh; omitted authorization
remaining read-only; forbidden refresh escalation; and unsupported registration and
authorization scopes. The explicit read-only case also models legacy default
registrations and checks that unauthorized requests cannot change their scope list.
`tests/test_compatibility.py` distinguishes unsupported scopes from registered-scope
mismatches through the combined K3s app. These are authored regressions, not a claim
of verified runtime or live-client behavior. Static lint/format and diff checks only.

## Earlier audit: tool scope negotiation (before DCR default fix)

The following is historical evidence for the earlier tool-metadata change. In
particular, its registration defaults and passing test count predate the fix above.

### Root cause and evidence boundary

The reported `Insufficient OAuth scope` comes from `remote_server.py:130-132`:
the authenticated token lacks the scope in `TOOL_SCOPES`. For
`relay_run_workflow` that is exactly `relay:execute` (`oauth/scopes.py:20`),
not `relay:write`. This check happens before any Relay API request or execution.
The pre-fix branch raised a plain `RelayAccessError`; it supplied no machine-readable
authorization challenge. Remote tool registration also advertised no tool-level
OAuth requirements. These are confirmed, reproducible scope-negotiation defects.

Public production discovery was checked read-only: both documents correctly
advertised all four supported scopes and the resource was
`https://mcp.relay.shaad.site/mcp`. The running image was
`relay-mcp:logo-20261031065705`. SHA-256 checks of deployed `remote_server.py`,
`tools.py`, `oauth/app.py`, `oauth/provider.py` and `oauth/scopes.py` matched this
checkout before the fix. Neither live token values nor the running in-memory client
registry/authorization requests were collected. The full live granted scope sets
and the exact point where ChatGPT omitted execution permission remain unobserved.

| Client observation | Permission implied by the enforced check |
| --- | --- |
| ChatGPT lists workflows | Its successful listing token includes `relay:read`. |
| ChatGPT cannot run workflows with this error | Its failing execution token lacks `relay:execute`. This does not establish every scope it has. |
| Claude runs workflows | Its successful execution token includes `relay:execute`. |

Client registrations have separate IDs and permitted scopes. There is no
ChatGPT/Claude name-based authorization branch, audience alias or scope conversion.
Both use the same resource and exact, case-sensitive, space-separated scope names.
Public, secret POST and Basic clients are supported. The synthetic client profiles
in regression tests are not claimed to be captures of either live client's requests.

### Scope flow audit

| Stage | Code and conclusion |
| --- | --- |
| Discovery | `oauth/app.py:144` builds authorization metadata from supported scopes; `remote_server.py:234-242` advertises protected-resource scopes. Live metadata is correct; supported scopes are not grants. |
| Dynamic registration | `oauth/app.py:57-59` defaults omitted scope to `relay:read`. Explicit scopes are validated by the SDK and stored by `oauth/provider.py:58-80`. |
| Authorization | `oauth/app.py:99-103` and `oauth/provider.py:82-96` require scopes to be supported and registered. Omitted scope grants registered read access only. Reconnecting with the same omitted/read-only scope cannot elevate access. |
| Consent and code | `oauth/consent.py:63-77` displays the requested permissions. `oauth/approval.py` requires authenticated approval, browser binding and CSRF. `oauth/codes.py:22-36` copies those scopes into the one-use, client/PKCE/resource-bound code. |
| Token issuance | `oauth/provider.py:102-138` issues opaque access/refresh tokens with exactly the code scopes and returns the same space-separated `scope`. No execution permission is lost here. |
| Validation and refresh | `oauth/provider.py:140-164` checks expiry, grant, client and audience; refresh permits only a subset of granted scopes. Bearer validation remains enabled, followed by `remote_server.py:130-132` and Relay's user/workspace checks. |

### Small secure fix

- `tools.py:34-46`: remote descriptors now expose each tool's exact OAuth scope
  through `_meta.securitySchemes`, derived from the same `TOOL_SCOPES` enforcement
  map. SDK 2.3.0 supports extension metadata through `_meta`; stdio remains unchanged.
- `oauth/scopes.py:27-58`: a specific scope-denial error produces an MCP error result
  with `_meta["mcp/www_authenticate"]`, `error="insufficient_scope"`, the discovery
  URL and only the missing required scope. It also explains the read-only
  registration case without exposing credentials.
- `remote_server.py:132`: the existing denial now uses that specific error. No scope
  defaults, consent requirements, audiences, token rules or execution code changed.

ChatGPT documents both tool security schemes and the tool-result authentication
challenge as requirements for triggering authorization UI:
[OpenAI authentication](https://developers.openai.com/plugins/build/auth).
Its [reference](https://developers.openai.com/plugins/reference) documents the
`_meta.securitySchemes` compatibility mirror. A challenge does not itself grant
access and cannot expand a read-only client's registered scope allowlist.

### Regression validation

The full MCP suite passes **57 tests**. Five new integration tests exercise real
SDK routes with synthetic client registrations and mocked Relay calls: metadata
matches enforcement for every tool; read-only reconnects remain denied; fresh
registration plus explicit execution consent succeeds; ChatGPT/Claude profiles
preserve scopes through code, access and refresh tokens; reduced scopes deny
execution; denied consent, forged tool metadata, malformed scopes and wrong audiences
do not bypass authorization. Denied calls never reach Relay, and challenge responses
contain no synthetic credentials. The stdio regression also asserts it gets no
OAuth tool metadata. No live workflows were executed or modified.

Run from `service/mcp-server`: `.venv/bin/python -m unittest discover -s tests -v`.
The complete suite needs execution outside this environment's sandbox because an
existing static-file test stalled inside it. Configured Ruff checks and formatting
of changed Python files, plus `git diff --check`, also pass.

### Deployment and existing connections — commands not executed

Only rebuild/redeploy MCP; no frontend build or workflow-engine deployment is needed.
From the repository root, use a unique image tag so the rollout cannot reuse the old
image (the existing deployment uses pull policy `Never`):

```sh
MCP_IMAGE="relay-mcp:oauth-scopes-$(date -u +%Y%m%d%H%M%S)"
docker build -t "$MCP_IMAGE" service/mcp-server
docker save -o /tmp/relay-mcp-oauth-scopes.tar "$MCP_IMAGE"
sudo k3s ctr -n k8s.io images import /tmp/relay-mcp-oauth-scopes.tar
sudo k3s kubectl -n relay set image deployment/relay-mcp relay-mcp="$MCP_IMAGE"
sudo k3s kubectl -n relay rollout status deployment/relay-mcp --timeout=300s
```

Import the image on every eligible node first. Preserve the single replica/worker
and `Recreate` strategy. Restart clears the in-memory registrations and tokens for
**both clients**, so recreate their connections after the final restart.

For listing and execution, configure ChatGPT's custom MCP registration with OAuth,
automatic client registration, and default scopes `relay:read relay:execute` in
Advanced OAuth settings when available. These scopes must be present at registration
and authorization, not merely in discovery. Do not add write/delete. On the Relay
consent page verify **Publish and execute workflows** appears before approval; if it
does not, the client has not requested execution. Refresh/reinstall the custom tool
definitions and verify listing, then a deliberately chosen workflow run. Configure
Claude with its required scopes through fresh consent as well. If a client cannot
request these scopes, use its supported OAuth configuration; do not loosen server
checks. Real client UI behavior still needs this post-deployment verification.

# Earlier audit: ChatGPT OAuth request compatibility

## Findings and evidence boundary

**The exact cause of the live ChatGPT `invalid_request` is not established.** Its
original response did not distinguish duplicate parameters, an unknown/missing client,
a missing/mismatched redirect, or a missing/non-S256 method. Each branch runs before
the SDK authorization handler. No production request values or live client registry
were inspected. Do not infer that ChatGPT omitted a parameter just because Relay
rejects its omission.

Confirmed, reproduced defects and fixes:

- Relay returned indistinguishable authorization errors. Static `error_description`
  messages now distinguish client registration, redirect, PKCE, response type,
  resource, scope and duplicate-parameter failures. Submitted values, codes,
  verifiers, state and credentials are not echoed by these diagnostics; no logging
  was added. Invalid redirects never receive a redirect response.
- SDK 2.3.0 metadata omitted `none`, although registration, authentication and
  exchange already support it. Metadata now advertises exactly `none`,
  `client_secret_post` and `client_secret_basic` for token exchange and revocation.
  Tests exercise all three methods. CIMD, private-key JWT and identity assertion
  support were not added or advertised.
- `Referrer-Policy: no-referrer` prevented the browser Referer fallback from working
  when Origin is absent. `same-origin` now permits Referer on same-origin form posts
  and suppresses it on external callbacks. Malformed Referer URLs fail closed with
  HTTP 403. A present Origin remains authoritative: a valid Referer cannot override
  a foreign or `null` Origin.

A lost client registration reproduces the reported error after restart. Fresh DCR
then succeeds. This is a plausible explanation for a *subsequent* attempt, not proof
of the live cause. After deployment, use the static diagnostic to identify the branch
without collecting raw authorization URLs, cookies, codes or PKCE material.

## Complete flow audit

| Stage | Contract and possible failures |
| --- | --- |
| Discovery | Unauthenticated `/mcp` returns 401 with a protected-resource metadata challenge. Both metadata endpoints use the configured public origin. Token methods now accurately include public clients. |
| Registration | Actual SDK `/register` returns 201 for supported public, secret POST and Basic clients. Omitted auth method defaults to secret POST. Unsupported scopes, grants and private-key JWT fail. |
| Storage | Client registrations are in memory. Restart discards them, including IDs that ChatGPT remembers. One replica/worker is required but does not provide persistence. |
| Authorization | Raw, form/query-decoded redirect strings must exactly equal a registered canonical URI before SDK URL normalization. Trailing-slash changes and alternate percent-encoding spellings fail. Normal URL encoding of request parameters works. |
| PKCE | Relay requires explicit `code_challenge_method=S256` and a valid 43-character challenge. The SDK defaults an omitted method internally, but Relay deliberately rejects omission and `plain`. No evidence establishes that ChatGPT omits it. |
| Resource | Authorization requires the exact public `/mcp` resource. Missing/wrong values fail with `invalid_target`. Token requests may omit resource to inherit the grant; explicit mismatches fail. Audience validation remains enabled. |
| Scopes | Requested scopes must be both supported and registered. Omission defaults to registered read-only access. Generic `relay`, `openid`, `offline_access` and arbitrary scopes are not silently accepted. |
| Browser binding | Signed HttpOnly/SameSite cookies (Secure on HTTPS) bind the pending request and CSRF token. Another active request cannot replace it; expired requests may be replaced. Pending requests last five minutes. |
| Login | Configured Origin or same-origin Referer plus valid CSRF is required. Relay `/auth/login` supplies server-side cookies; `/auth/me` verifies user/workspace. Passwords are never retained. |
| Approval | Authenticated user explicitly Approves or Denies. Both consume the pending request. Only approval creates a 60-second code bound to client, redirect, challenge, resource, scopes, verified user and their Relay session. |
| Exchange | SDK client authentication, code/client/expiry/redirect checks and actual SHA-256 verifier comparison run before provider exchange. Relay guards raw redirect, verifier syntax and resource. The provider consumes the code exactly once on success. |
| Tokens | Opaque access tokens expire after five minutes; grants/refresh last at most one hour. Refresh rotates both tokens; revocation removes the grant and pair. |
| MCP | SDK bearer authentication and exact provider audience checking protect every request. Initialization and all 16 tools remain available. Each workflow operation checks scope, revalidates Relay user/workspace and uses its own HTTP client. Relay remains authoritative for resource permissions. |

Inspected installed SDK `provider.py`, `routes.py`, `handlers/authorize.py`,
`handlers/token.py`, `handlers/register.py`, `handlers/metadata.py`,
`middleware/client_auth.py`, and the existing Relay revocation adapter. `TokenHandler`
really verifies S256; advertised PKCE alone was not assumed sufficient. Its code and
refresh hooks do not receive resource, so Relay's resource guards remain necessary.
The supported SDK metadata builder/handler are reused without monkey-patching.

The installed SDK requires body `client_id` even with Basic authentication. Tests
exercise that contract. Header-only Basic is a known remaining SDK limitation, not
an established cause of the `/authorize` failure; no speculative adapter was added.

Official OpenAI documentation describes DCR once per connection with client-ID reuse,
S256, resource binding, and accurate authentication-method metadata:
[Authentication](https://developers.openai.com/plugins/build/auth).
Its [troubleshooting guide](https://developers.openai.com/plugins/deploy/troubleshooting)
advises checking that the registered client still exists.

## Browser and connection limitations

Neither Origin nor Referer: still rejected, even with cookies. Use a supported
top-level browser/popup that supplies Origin or honors same-origin Referer policy;
do not bypass CSRF/origin validation. Third-party cookie blocking or iframe restrictions
may require a normal browser. ASGI tests cannot prove behavior in ChatGPT's embedded
browser. OAuth HTML now loads `/oauth/static/relay.css` from the same application;
the former inline stylesheet was blocked by `default-src 'none'`. The existing
Docker `COPY oauth/ ./oauth/` includes this asset without packaging changes.

HTML uses `default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; base-uri 'none';
frame-ancestors 'none'`. On the signed-in consent page only, `form-action` additionally
allows the pending request's already-validated callback URL (without query/fragment).
This is necessary because Chromium also checks redirects following form submissions:
restricting it to `'self'` would block the external OAuth callback. This does not
change server-side redirect matching. No wildcard callback origins are allowed.
See [MDN form-action](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/form-action).
Scripts, inline styles and framing remain blocked. JSON/MCP responses retain the
previous strict CSP; OAuth HTML remains `no-store`. Styling uses local system fonts,
with no external assets or JavaScript. Application names are escaped and are explicitly
not presented as verified identities.

Trusted-ingress peer checks still precede forwarded-header handling. No proxy trust,
TLS or network configuration was changed. Existing in-memory storage, expiry and
rate-limit limitations remain. No persistence was added for a test connection.

If the new error says `Unknown client registration; register again after a server
restart`, recreate ChatGPT's MCP connection to trigger fresh DCR. Retrying the same
unknown client cannot work. **Recreate after the final MCP restart**, which itself
clears all registrations and tokens. If fresh registration still fails, follow the
new safe diagnostic rather than relaxing parameter checks.

## Validation and files

All **47 tests pass**, including six new compatibility tests plus existing OAuth,
deployment, two-user isolation and stdio regressions. Before fixes, the new suite
reproduced 14 assertion failures (diagnostic subcases/restart, metadata and referrer
policy). After fixes the full mocked path includes real SDK routes, Relay login via
HTTP mock transport, consent, public-client PKCE exchange, initialization, 16-tool
discovery, read-only listing for two workspaces, refresh and revocation. All three
advertised client-auth methods work. No live Relay workflows were read or mutated.

Executed from `service/mcp-server` using its virtual environment:

```sh
python -m py_compile oauth/*.py
python -m unittest discover -s tests -v
```

Also passed `git diff --check` and configured Ruff lint for `service/mcp-server`.
The full suite ran outside the sandbox because the existing stdio subprocess test
hangs inside it. Changed in this audit: `oauth/app.py`, `oauth/origin.py`,
`oauth/login.py` (import order only), `tests/test_compatibility.py`, and this document.

## Manual deployment commands — not executed

The inspected manifest uses namespace `relay`, deployment/container `relay-mcp`,
image `relay-mcp:dev`, pull policy `Never`, **one replica**, and `Recreate` strategy.
Confirm the running deployment matches before executing. From repository root:

```sh
docker build -t relay-mcp:dev service/mcp-server
docker save -o /tmp/relay-mcp-dev.tar relay-mcp:dev
sudo k3s ctr -n k8s.io images import /tmp/relay-mcp-dev.tar
sudo k3s kubectl -n relay get deployment relay-mcp -o wide
sudo k3s kubectl -n relay rollout restart deployment/relay-mcp
sudo k3s kubectl -n relay rollout status deployment/relay-mcp
```

Import the archive on every eligible K3s node before restart, or scheduling may use
an old/missing image. Only MCP is restarted; no manifests, secrets, networking, TLS,
replica counts or other deployments are changed. Recreate causes brief downtime and
loses in-memory OAuth state. Keep one replica; the runner enforces one worker.

Read-only public verification after restart:

```sh
curl --fail --silent --show-error https://mcp.relay.shaad.site/.well-known/oauth-authorization-server
curl --fail --silent --show-error https://mcp.relay.shaad.site/.well-known/oauth-protected-resource/mcp
curl --silent --show-error --include https://mcp.relay.shaad.site/mcp
```

Expect both metadata endpoints to return 200, auth methods to include `none`, PKCE to
advertise only S256, and the resource to be the public `/mcp` URL. Unauthenticated MCP
must still return 401 with a Bearer resource-metadata challenge. These checks do not
prove ChatGPT login: recreate its connection, approve read-only access and verify
tool discovery/listing. Do not paste secrets, cookies or authorization URLs into
reports. Nothing was deployed, committed or merged by this audit.

The OAuth screens reuse the original `frontend/public/brand/relay/relay-light.png`
logo (copied into `oauth/static/` for standalone Docker packaging), the frontend
dark theme tokens, and its login form control styling. Images are same-origin only.
