# ChatGPT OAuth compatibility audit

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
