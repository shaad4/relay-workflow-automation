# Relay MCP OAuth — Phase 2, Batch 1

The OAuth-only factory remains available for a **single-process, loopback-only
local demonstration**. Batch 2 adds the combined protected MCP application; see
[the MCP README](../README.md). The OAuth-only factory does not serve MCP tools. Keep the existing Codex stdio
entry point (`../start_mcp.sh`) unchanged. Do not publish, tunnel, reverse-proxy, or
bind this application to a public interface.

## Run locally

From `service/mcp-server`, use the existing virtual environment and requirements
(`mcp==2.3.0`). Set `RELAY_API_URL` to the existing trusted Relay API, and set
`MCP_SESSION_SECRET` to a cryptographically random secret of at least 32 characters
(for example, generate it with `secrets.token_urlsafe(32)`; never commit it).
`MCP_PUBLIC_ORIGIN` defaults to `http://127.0.0.1:8001`; only loopback origins are
accepted. It must match the browser URL exactly. Then run:

```sh
.venv/bin/uvicorn oauth.app:create_oauth_app --factory --host 127.0.0.1 --port 8001 --no-access-log
```

Use one worker, without reload. The app factory accepts a shared provider, or the
original pending-request store as its positional argument. All routes use that
provider's stores. No server was deployed as part of this batch.

## Authorization flow

1. Register through `POST /register`, with canonical, exact redirect URI strings,
   `authorization_code` and optionally `refresh_token` grants, and explicit scopes from `relay:read`, `relay:write`, `relay:execute`, `relay:delete`.
   Omitting `scope` registers all supported scopes as eligible for later requests;
   an explicit list stays restricted. Registration does not grant user access.
   Omitted authorization scope still defaults to read-only; other permissions
   require an explicit request and approval. Legacy read-only registrations need
   fresh registration before requesting more scopes; refresh cannot expand grants.
   Public clients use `token_endpoint_auth_method=none`; secret-based SDK methods
   are supported too. Redirects must use HTTPS or HTTP loopback, without fragments
   or embedded credentials. Registration is not a statement that a client is trusted.
2. Send `GET` or form `POST /authorize` with `response_type=code`, `client_id`,
   explicit exact `redirect_uri`, `code_challenge_method=S256`, a valid SHA-256
   challenge, `resource=http://127.0.0.1:8001/mcp` (adjust for the configured origin),
   and optional scope/state. Always use unpredictable state in real clients.
3. The browser receives a signed HttpOnly, SameSite=Lax session cookie containing
   only random identifiers and CSRF state. The consent page displays the client ID
   and requested scopes. Login posts to the existing Relay `/auth/login`, then
   verifies the resulting bearer credential with `/auth/me`. Passwords are never
   retained. Relay tokens remain only in a server-side `UserRelaySession`.
4. Login and approval require the configured Origin plus a session-bound CSRF token.
   Login rotates CSRF state. Approve consumes the pending request and creates a
   60-second code tied to the client, exact redirect, challenge, resource, verified
   user ID, and that user's Relay session. Deny consumes the request and returns
   `access_denied`. Both preserve state and delete the temporary login record.
5. `POST /token` exchanges the code with the original redirect and PKCE verifier.
   The SDK authenticates the client and verifies S256; the provider atomically
   consumes the code and issues random opaque access/refresh tokens. Invalid
   exchange attempts do not consume a valid code. Access lasts 5 minutes. The
   delegated grant and refresh token last at most one hour from initial exchange.
6. Refresh checks client and scope, retains the original audience/user/session,
   and rotates both tokens, immediately invalidating the previous pair. It never
   extends the grant's absolute expiry. `POST /revoke` with either current token
   invalidates both tokens and releases the delegated session. Wrong-client and
   unknown-token revocation return success without revoking another client's grant.

`load_access_token` checks expiry and the configured resource. Token requests may
omit `resource` to inherit the grant's audience; an explicitly different resource
is rejected for both grant types. No request can change audience. Delegated sessions
are accessible internally through the token's grant record. The Batch 2 combined
application routes these sessions to protected tools. No OAuth route uses `RelaySession` or the stdio account.

## SDK 2.3.0 source findings

Inspected the installed `mcp/server/auth/provider.py`, `routes.py`,
`handlers/{authorize,token,register,revoke}.py`, `middleware/client_auth.py`,
`settings.py`, and `mcp/shared/auth.py` before implementing:

- `create_auth_routes` supplies metadata, authorization, token, registration and
  revocation. The provider implements the actual declared client/code/token hooks.
  Identity assertions remain disabled and unsupported.
- `AuthorizationHandler` supports only S256 but defaults an omitted method to
  S256. Relay requires the method explicitly. `AuthorizationParams` contains the
  challenge, not a verifier or method.
- `TokenHandler` **does compute SHA-256 and compare the verifier hash**, after client,
  expiry and redirect validation and before calling `exchange_authorization_code`.
  Provider exchange hooks receive no verifier. Do not call them directly from an
  unvalidated HTTP endpoint. Loading a code must not consume it; exchange must.
- Token request models accept `resource`, but the handler does not validate it or
  pass it into code/refresh exchange hooks. Relay's route guard checks it before
  invoking that handler; all stored grants also carry the sole configured audience.
- Pydantic normalizes URLs before SDK comparisons. Relay validates raw redirect
  strings first, including before SDK error redirects, and requires canonical
  registration strings. It also rejects duplicate form/query parameters and
  validates PKCE challenge/verifier syntax.
- `RevocationRequest.client_secret` is nullable but lacks a default in this SDK,
  so its stock handler rejects omission even for public/Basic clients. The small
  `revocation.py` adapter uses SDK client authentication and request validation,
  supplying the missing default without bypassing authentication.

## Limits and security boundaries

- Memory only: restart loses clients, pending requests, codes, browser logins and
  grants. Existing cookies/tokens become unusable. No multi-worker consistency or
  cross-process atomicity. Exchange is atomic only within one event loop.
- Expired pending requests (5 minutes), login sessions (10 minutes), codes, tokens
  and grants are removed opportunistically on incoming requests/provider activity.
  Idle memory is not swept by a background task; expiry is still checked before use.
  Client registrations persist until restart. No hard store quotas, rate limiting,
  registration governance, distributed replay protection or production audit system.
- HTTP loopback cookies cannot have Secure enabled; configured HTTPS uses Secure.
  This exception is strictly for local demonstration. Host validation, configured
  Origin checking, CSRF, no-store, no-referrer, frame denial and a 64 KiB body limit
  are enabled. Browser-client CORS support is not provided on guarded endpoints.
- Relay identity is verified at login. OAuth refresh rotates OAuth tokens only;
  it does not refresh Relay credentials. The Batch 2 tool router revalidates Relay
  identity and workspace before operations and enforces per-tool scopes. The
  one-hour OAuth grant lifetime does not guarantee Relay session validity.
- Credentials/tokens are plaintext in process memory, not encrypted persistence.
  Revocation removes server references; it cannot guarantee memory zeroization or
  revoke Relay's own sessions. Used refresh tokens are invalidated, but there is no
  retained replay history that revokes a newer pair after an old-token replay.
- Do not expose publicly: the controls above do not make this a production identity
  service. Remote deployment remains deferred; Batch 2 provides local multi-user MCP routing.

## Validation

From the repository root:

```sh
service/mcp-server/.venv/bin/python -m unittest discover -s service/mcp-server/tests -v
```

Tests exercise the real SDK handlers via ASGI, including PKCE failure, wrong clients,
redirect/resource mismatch, code expiry/replay/concurrent exchange, denial, CSRF,
origin checks, confidential-client authentication, refresh rotation, revocation,
expiry cleanup and two-user session isolation. Auth Service contract tests use an
HTTP mock transport, never real accounts or a live Relay mutation.
