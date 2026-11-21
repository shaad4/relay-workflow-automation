# Endpoint rate limiting

Relay limits login attempts, email requests and workflow triggers. When a limit is reached, the caller receives HTTP `429 Too Many Requests`. Read the `Retry-After` header for the number of seconds to wait. A rejected trigger never reaches Kafka.

## Default limits

Paths below are service paths. Requests sent through the frontend start with `/api/relay`, for example `POST /api/relay/auth/login`.

| POST endpoint | Counted by | Default |
|---|---|---|
| `/auth/login` | Account | 10 failed logins per 15 minutes |
| `/auth/forgot-password` | Account | 5 requests per hour |
| `/auth/resend-verification` | Account | 5 requests per hour, shared with verification emails triggered by login |
| `/workflows/{workflow_id}/run` | Authenticated user and workspace | 10 requests per user and 60 per workspace each minute |
| `/hooks/{public_token}` and `/hooks/{public_token}/test` | Resolved webhook ID and workspace | 60 requests per webhook and 300 per workspace each minute, shared by live and test calls |

At the public edge, login, registration, password reset, forgotten-password and verification-resend requests also have an IP limit of 10 per minute with an initial burst of 10. Webhook traffic has a separate IP limit of 120 per minute with a burst of 120. Edge limits refill continuously. Clients sharing a public IP share capacity on that proxy instance.

## Where counts live

- **Nginx or Traefik** counts client IPs at the public entry point, before the request reaches Next.js. Nginx uses shared memory across its workers. Each Traefik instance maintains its own buckets. Ensure the edge receives the original client address. If another load balancer sits in front, preserve the source IP or configure the edge to accept client addresses only from that trusted hop. Relay's services never choose a quota using a caller-supplied IP header.
- **Auth Service** uses the existing Redis 7 server. Keys contain a keyed digest (HMAC) of the normalized email, scoped to login, recovery or verification. Known and unknown emails consume the same recovery quota. Login reserves a slot before checking credentials and refunds a successful login in its original window. In-flight checks temporarily occupy slots. An unverified login returning 401 consumes a slot.
- **Integration Service** checks manual runs after authentication and webhook deliveries after webhook lookup and any configured secret check. It charges all applicable quotas in one Redis operation before payload processing, workflow validation or publication. A request rejected by one quota leaves the other quota available. An admitted request that subsequently fails validation still uses a slot.

Application counters use the prefix `relay:ratelimit:` in Redis database 2 by default. Each key expires at a fixed boundary based on the Redis clock. For example, a manual run rejected at 12:00:45 can retry in 15 seconds. Traffic can burst on either side of a window boundary. If Redis is unavailable during admission, the protected operation returns HTTP 503 with `Retry-After: 1`.

## Configure and deploy

| Setting | Service | Default |
|---|---|---|
| `RATE_LIMIT_REDIS_URL` | Auth and Integration | `redis://rag-redis:6379/2` in Compose, `redis://redis:6379/2` in full K3s |
| `RATE_LIMIT_LOGIN_FAILURES` | Auth | 10 per 15 minutes |
| `RATE_LIMIT_EMAIL_REQUESTS` | Auth | 5 per hour for each email quota |
| `RATE_LIMIT_MANUAL_PER_USER` | Integration | 10 per minute |
| `RATE_LIMIT_MANUAL_PER_WORKSPACE` | Integration | 60 per minute |
| `RATE_LIMIT_WEBHOOK_PER_HOOK` | Integration | 60 per minute |
| `RATE_LIMIT_WEBHOOK_PER_WORKSPACE` | Integration | 300 per minute |

Set positive integer limits in the service environment and restart all replicas of that service together. Point replicas at the same Redis database. The existing Celery broker can continue using its own database on the same server. For a password-protected Redis instance, put the connection URL in the service secret.

- **Docker Compose.** Rebuild Auth and Integration. The service env examples configure Redis. To activate the IP limits, apply the rate-limit maps, zones and server directives from the [Nginx example](../deploy/docker/nginx.conf.example) to your public HTTPS site, validate with `nginx -t` and reload. Apply the same rules to a separately exposed gateway hostname. Plain local Compose uses the application quotas; the edge limits require the proxy.
- **Full K3s.** Apply the ingress changes from the [full K3s overlay](../deploy/kubernetes/overlays/full-k3s) with your reviewed hostname. Traefik needs its Kubernetes CRD provider and the `Middleware` CRD. The two path-specific Ingress resources reference middleware in the `relay` namespace. Existing installations that update only images through CD must also apply these ingress resources and middleware. Check that both limited Ingress resources have the same public hostname and TLS secret as the main Ingress.
- **Hybrid Kubernetes.** Configure `RATE_LIMIT_REDIS_URL` in both service Secrets with the private Redis address. Include the ingress component if Traefik is your public edge. Route public traffic through the configured proxy and keep the underlying services private.

## Verify

In development, set `RATE_LIMIT_MANUAL_PER_USER=1`, restart Integration and run a published manual workflow twice with the same user in the same minute. The first request should return 202. The second should return 429 with a positive retry delay and create no second execution. Retry after the delay and restore the desired limit after testing.

The auth suite includes real Redis checks for concurrent requests, expiry and login refunds. Set `RATE_LIMIT_TEST_REDIS_URL` to a disposable Redis 7 database when running that suite. CI supplies this database. Route tests also check that rejected requests skip email, validation and Kafka work.
