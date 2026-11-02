# Relay MCP server

The server exposes the same 21 tools over two transports:

- **stdio:** `start_mcp.sh` runs `server.py` with a single-account `RelaySession`.
- **Streamable HTTP:** `remote_server.py` serves `/mcp` and OAuth routes in one
  ASGI application. Each authorized user has a separate delegated Relay session.

Install `requirements.txt` in a service-local virtual environment. Keep credentials
in local environment configuration or deployment Secrets, never in source control.

## Local HTTP startup

From `service/mcp-server`:

```sh
export RELAY_API_URL=https://relay.shaad.site/api/relay
export MCP_PUBLIC_ORIGIN=http://127.0.0.1:8001
# Supply MCP_SESSION_SECRET: a cryptographically random value of at least 32 characters.
.venv/bin/python remote_server.py
```

Local mode binds to `127.0.0.1:8001`, rejects non-loopback peers and untrusted
Host/Origin headers, and disables access logs and proxy-header trust. Use one
process. The protected resource is `http://127.0.0.1:8001/mcp`.

The stdio launcher reads `.env.local` with `RELAY_API_URL`, `RELAY_EMAIL` and
`RELAY_PASSWORD`. It currently expects the checkout path specified in `start_mcp.sh`.

## K3s mode

Set `MCP_DEPLOYMENT_MODE=k3s`, `MCP_PUBLIC_ORIGIN=https://mcp.relay.shaad.site`,
`MCP_PORT=8001`, and `MCP_TRUSTED_PROXY_IPS` to the actual ingress peer IPs or
narrowly scoped CIDRs. Supply `MCP_SESSION_SECRET` and `RELAY_API_URL` through
Secrets/configuration. Run `remote_server.py`, as in the image's Dockerfile.

K3s mode binds to `0.0.0.0:$MCP_PORT`. Keep one worker and one replica because OAuth
sessions and tokens are held in memory. The original socket peer must match the
trusted ingress allowlist before forwarded headers are interpreted. Wildcards and all-address CIDRs
are rejected; forwarded host headers cannot replace the configured public origin.

The separate manifests are in [deploy/kubernetes/mcp](../../deploy/kubernetes/mcp/).
They require the referenced Secrets/configuration and TLS ingress to be provisioned.
The release workflow updates an existing `relay-mcp` deployment. Configure Traefik
to terminate HTTPS, preserve Host and sanitize forwarded headers. Use ingress-only
network access and the narrowest valid trusted proxy ranges.

Client registrations use Python's built-in SQLite support. The MCP manifests set
`MCP_CLIENT_DB_PATH=/data/oauth.sqlite` and mount the `relay-mcp-data` PVC there;
include `storage.yaml` when deploying this change. Keep the PVC when replacing
the Pod. Image-only CD does not install the PVC or mount: deploy those settings
with the updated MCP image, retaining the production image reference rather than
the manifest's development placeholder. The container uses `fsGroup: 10001` for
volume access, and the database file is restricted to mode 0600 because registrations
can contain client secrets.
Back it up while MCP is stopped. K3s local-path storage does not survive node/disk loss.
For local persistence, set `MCP_CLIENT_DB_PATH` to a file in an existing private,
writable directory; leaving it unset uses an in-memory SQLite database.

## OAuth and scopes

Discovery endpoints:

- `/.well-known/oauth-authorization-server`
- `/.well-known/oauth-protected-resource/mcp`

Clients register at `/register`, authorize at `/authorize`, complete browser login
and consent, and exchange the authorization code at `/token`. Revocation is at
`/revoke`. Send an OAuth bearer token on every MCP request, including discovery of
tools; initialize with the SDK's required protocol and Accept headers.

Authorization requires an exact registered redirect URI, explicit S256 PKCE and
the configured `/mcp` resource audience. Login and consent enforce Origin and
session-bound CSRF protection. Credentials remain server-side. Codes expire after
60 seconds; access tokens after five minutes; delegated grants/refresh tokens after
at most one hour. Refresh rotates both tokens without extending the grant or
increasing scopes. Revoking either current token invalidates the pair.

| Scope | Tools |
| --- | --- |
| `relay:read` | `relay_get_node_schema`, `relay_validate_workflow_definition`, `relay_list_ai_models`, `relay_list_connections`, `relay_list_ai_provider_connections`, `relay_list_workflows`, `relay_list_executions`, `relay_get_execution_steps` |
| `relay:write` | `relay_create_workflow`, `relay_add_node`, `relay_update_node`, `relay_add_edge`, `relay_validate_workflow`, `relay_create_complete_workflow` |
| `relay:execute` | `relay_publish_workflow`, `relay_deactivate_workflow`, `relay_run_workflow` |
| `relay:delete` | `relay_delete_workflow`, `relay_delete_node`, `relay_delete_edge` |

`relay_hello` requires authentication but no additional scope. Omitting scopes at
registration permits subsequent requests for all four scopes; it does not grant
access. Omitting authorization scopes requests read-only access. Explicit
registration scopes remain a ceiling; refresh cannot expand them.

To list and run workflows, register and authorize `relay:read relay:execute`.
Existing clients registered only for read access need new registration before
requesting execution permission. Remote tool descriptors advertise required scopes
in `_meta.securitySchemes`; scope denials include an MCP authentication challenge.
Clients still need explicit user consent for additional permissions.

For every tool call, the server checks the token, scope and grant, creates an
isolated HTTP client, and revalidates the user's Relay identity and workspace before
each API request. Identity overrides in tool arguments are rejected. The HTTP
client closes after the invocation. Expired/revoked Relay sessions require a fresh
login; there is no fallback account or silent refresh of delegated sessions.

## Connection discovery

Before creating or updating nodes that need a connection, clients can look up IDs
without asking the user to copy them:

- `relay_list_connections(provider="gmail")` returns saved Gmail connections with
  `id`, `name` (for example, `Gmail - person@example.com`), `provider`, `auth_type`,
  `email`, and `status: "configured"`. Omit `provider` to list all app connections,
  including HTTP connections. Non-Gmail connections have `email: null`.
- `relay_list_ai_provider_connections(provider="openai")` returns AI connections
  with `id`, `name`, `provider`, and their saved `status` (`active` or `inactive`).
  Omit `provider` to list all AI connections; `gemini` and `anthropic` are also
  supported. Inactive connections are included so clients can explain why a
  saved connection cannot be used.

Provider filters ignore case and surrounding whitespace. Both tools return an
empty list if no connection matches and only read the authenticated workspace.
They return an explicit allowlist of metadata; credentials, API keys, tokens, and
raw configuration are excluded in both transports.

Use the selected result's `id` as `configuration.connection_id` in the appropriate
app or AI node. Match the user's requested connection name or Gmail account; if
multiple connections remain ambiguous, ask which named account to use. If none
exist, the user must connect the app/provider in Relay. AI nodes require an active
connection. Saved/configured or active status does not verify live provider health.

Both tools require `relay:read` over HTTP. Restart/redeploy the MCP server and
refresh the client's tool list to expose them to existing clients.

## Authoring workflows with an LLM

The server's initialization instructions and creation-tool descriptions tell clients
to discover contracts before constructing a workflow. The tools expose that guidance
directly; clients do not need repository access or an independently maintained prompt.

1. Call `relay_get_node_schema()` for all supported types, or pass `node_type`, for
   example `ai.generate`. The Workflow Service generates configuration JSON Schemas
   from its actual Pydantic validators and returns output schemas, examples,
   expression rules, and edge conditions. Example IDs/models are placeholders.
2. Discover app/AI connections by name. Call `relay_list_ai_models(connection_id)`
   for the chosen active AI connection. Choose a returned model appropriate for
   text/structured generation; provider catalogs may include other model types.
3. Build the graph using `{{trigger.data.<field>}}` for incoming data and
   `{{nodes.<node_id>.<field>}}` for previous outputs. Trigger IDs such as
   `trigger_1` are not expression roots. There is no extra `.output` wrapper.
4. Call `relay_validate_workflow_definition(nodes, edges, sample_input)` before
   saving. `sample_input` is optional raw trigger data, e.g.
   `{"research_topic": "How RAG works"}`. This operation performs no actions,
   provider generation, or database writes. It returns structured `node_id`,
   `field`, `expression`, and `suggestion` details when applicable.
5. Correct errors, create the draft, and validate the saved version before asking
   for publication/execution approval. `relay_create_complete_workflow` performs
   preflight automatically and returns `status: "invalid_definition"` without
   creating a workflow when validation fails. It also accepts `sample_input`.

AI Generate accepts `connection_id`, `model`, `prompt`, and optional `instructions`
and `rag_context`. It does not accept `provider`, `input_mappings`, or output format
configuration. Provider comes from the AI connection. Generated text is available
as `{{nodes.generate_1.content}}`, alongside `model`, `input_tokens`, `output_tokens`.

`relay_add_edge` and complete-workflow edges support `condition`: use an exact
branch value for `logic.condition`, or `approved`/`rejected` for `human.approval`.
Referenced output nodes must execute before the consumer on every incoming path.
HTTP body properties and legacy root aliases remain dynamic; known AI output
fields are checked. Trigger data fields are only checked for existence when a
sample is supplied. Provider health and future payload values remain runtime checks.

The backing endpoints are `GET /workflows/node-types/` (optional `node_type` query)
and `POST /workflows/validate-definition/`. They require Relay authentication.
Saved-version validation and publication use the same validation implementation,
including expression checks, regardless of whether a caller uses MCP, the UI, or
the API. Historical published definitions are not rewritten. Runtime expression
failures report `UNRESOLVED_EXPRESSION` with a field and, where available, the
original reference; they do not expose resolved payload values in the error.

## Keeping contracts aligned

`service/workflow-service/app/contracts/` owns the shared expression syntax and
AI Generate input/output models. Independently built service images use generated
copies in `service/execution-service/app/contracts/`. After changing the source,
run from the repository root:

```sh
python scripts/sync_workflow_contracts.py
python scripts/sync_workflow_contracts.py --check
```

CI rejects stale copies. Authoring permits connection-ID expressions; execution
validates the resolved UUID using the same model with `context={"resolved": True}`.
Both paths enforce the same supported fields and text limits. Changes should be
deployed to Workflow Service, Execution Service, and API Gateway before the MCP
server, then clients should refresh discovery. The contract response includes
`contract_version` for future incompatible changes.

## Assets and operational limits

The HTTP server advertises `/oauth/static/relay-icon-black.png` in server metadata.
The OAuth logo, icon and stylesheet are bundled under `oauth/static/`; clients may
cache server metadata and need reconnection after an image change.

Client registrations survive restarts when the SQLite file is on persistent storage.
Pending requests, tokens, grants and delegated credentials remain in process memory;
users must sign in again after a restart. Multiple workers cannot share that session
state. Registrations lost before this change require one fresh registration. Expiry
cleanup is opportunistic; quotas and production rate limiting are not provided.

Scope checks narrow Relay access; Relay's API remains responsible for resource and
workspace authorization. Revocation cannot undo mutations already accepted by
Relay. Mutations are not automatically retried, and multi-step workflow creation
may leave a partial draft after failure. Inspect uncertain outcomes before retrying.
Credential redaction does not remove all sensitive user-created workflow data.
