// Server-only implementation: import from route handlers, never from client components.
export const PROXY_PREFIX = "/api/relay";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function configuredOrigin(value, setting) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${setting} must be an HTTP(S) origin`);
  }
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new Error(`${setting} must be an HTTP(S) origin`);
  }
  return url.origin;
}

export function proxyConfig(env = process.env) {
  if (
    env.NODE_ENV === "production" &&
    (!env.API_GATEWAY_URL || !env.FRONTEND_URL)
  ) {
    throw new Error(
      "API_GATEWAY_URL and FRONTEND_URL are required in production",
    );
  }
  const gateway = configuredOrigin(
    env.API_GATEWAY_URL || "http://127.0.0.1:8001",
    "API_GATEWAY_URL",
  );
  const frontend = configuredOrigin(
    env.FRONTEND_URL || "http://localhost:3000",
    "FRONTEND_URL",
  );
  const timeout = Number(env.API_PROXY_TIMEOUT_SECONDS || 120);
  const maxBody = Number(env.API_PROXY_MAX_BODY_BYTES || 12582912);
  if (
    !Number.isInteger(timeout) ||
    timeout < 1 ||
    timeout > 600 ||
    !Number.isInteger(maxBody) ||
    maxBody < 1 ||
    maxBody > 104857600
  ) {
    throw new Error("Invalid API proxy limits");
  }
  return { gateway, frontend, timeout, maxBody };
}

function errorResponse(status, detail) {
  return Response.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

export function trustedMutation(request, frontend) {
  if (SAFE_METHODS.has(request.method)) return true;
  const origin = request.headers.get("origin");
  if (origin) return origin === frontend;
  if (request.headers.get("sec-fetch-site") === "cross-site") return false;
  // Non-browser webhook clients have no Origin or cookies. Cookie-authenticated
  // mutations require an explicit origin (or same-origin Referer for older clients).
  if (request.headers.has("cookie")) {
    try {
      return new URL(request.headers.get("referer")).origin === frontend;
    } catch {
      return false;
    }
  }
  return true;
}

export function proxyCookie(cookie) {
  return cookie
    .replace(/;\s*domain=[^;]*/gi, "")
    .replace(/(;\s*path=)(\/auth(?:\/[^;]*)?)(?=;|$)/gi, `$1${PROXY_PREFIX}$2`);
}

export function proxyLocation(value, target) {
  const location = new URL(value, target);
  if (!["http:", "https:"].includes(location.protocol)) return null;
  return location.origin === target.origin
    ? `${PROXY_PREFIX}${location.pathname}${location.search}${location.hash}`
    : location.href;
}

async function readChunk(reader, signal) {
  signal.throwIfAborted();
  let onAbort;
  const aborted = new Promise((_, reject) => {
    onAbort = () => {
      // A custom stream's cancel() may itself never settle; never await it.
      reject(signal.reason);
      void reader.cancel(signal.reason).catch(() => {});
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
  try {
    return await Promise.race([reader.read(), aborted]);
  } finally {
    signal.removeEventListener("abort", onAbort);
  }
}

async function boundedBody(request, maxBody, signal) {
  if (!request.body) return undefined;
  if (Number(request.headers.get("content-length")) > maxBody)
    throw new RangeError("body limit");
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await readChunk(reader, signal);
      signal.throwIfAborted();
      if (done) break;
      size += value.byteLength;
      if (size > maxBody) {
        void reader.cancel().catch(() => {});
        throw new RangeError("body limit");
      }
      chunks.push(value);
    }
  } finally {
    if (signal.aborted) void reader.cancel(signal.reason).catch(() => {});
    reader.releaseLock();
  }
  return Buffer.concat(chunks, size);
}

export async function proxyRequest(
  request,
  { env = process.env, fetchImpl = fetch } = {},
) {
  let config;
  try {
    config = proxyConfig(env);
  } catch {
    return errorResponse(503, "API proxy is not configured");
  }
  if (!trustedMutation(request, config.frontend))
    return errorResponse(403, "Untrusted request origin");
  // One deadline covers body reception, the upstream request and its response.
  const signal = AbortSignal.any([
    request.signal,
    AbortSignal.timeout(config.timeout * 1000),
  ]);
  const incoming = new URL(request.url);
  if (!incoming.pathname.startsWith(`${PROXY_PREFIX}/`))
    return errorResponse(404, "Not found");
  const target = new URL(config.gateway);
  // Assign only pathname/search: neither user input nor redirects can select an upstream host.
  target.pathname = incoming.pathname.slice(PROXY_PREFIX.length);
  target.search = incoming.search;
  const headers = new Headers(request.headers);
  const connectionTokens = (headers.get("connection") || "")
    .split(",")
    .map((value) => value.trim().toLowerCase());
  for (const name of [...headers.keys()]) {
    if (
      HOP_HEADERS.has(name) ||
      connectionTokens.includes(name) ||
      ["host", "content-length", "forwarded", "x-real-ip"].includes(name) ||
      name.startsWith("x-forwarded-")
    )
      headers.delete(name);
  }
  headers.set("accept-encoding", "identity");
  let body;
  try {
    body = SAFE_METHODS.has(request.method)
      ? undefined
      : await boundedBody(request, config.maxBody, signal);
  } catch (error) {
    if (signal.aborted) {
      return errorResponse(
        request.signal.aborted ? 400 : 408,
        request.signal.aborted
          ? "Request was cancelled"
          : "Request body timed out",
      );
    }
    return errorResponse(
      error instanceof RangeError ? 413 : 400,
      "Request body could not be accepted",
    );
  }
  try {
    const response = await fetchImpl(target, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
      cache: "no-store",
      signal,
    });
    const responseHeaders = new Headers(response.headers);
    const responseConnectionTokens = (responseHeaders.get("connection") || "")
      .split(",")
      .map((value) => value.trim().toLowerCase());
    for (const name of [...responseHeaders.keys()]) {
      if (
        HOP_HEADERS.has(name) ||
        responseConnectionTokens.includes(name) ||
        ["set-cookie", "content-length", "content-encoding"].includes(name) ||
        name.startsWith("access-control-")
      )
        responseHeaders.delete(name);
    }
    for (const cookie of response.headers.getSetCookie())
      responseHeaders.append("set-cookie", proxyCookie(cookie));
    const location = response.headers.get("location");
    if (location) {
      const rewritten = proxyLocation(location, target);
      if (!rewritten) return errorResponse(502, "Invalid API redirect");
      responseHeaders.set("location", rewritten);
    }
    responseHeaders.set("cache-control", "no-store");
    return new Response(request.method === "HEAD" ? null : response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    // Never include upstream URLs, credentials, response bodies, or network errors.
    return errorResponse(502, "API service unavailable");
  }
}

export async function gatewayReady({
  env = process.env,
  fetchImpl = fetch,
} = {}) {
  try {
    const { gateway } = proxyConfig(env);
    const response = await fetchImpl(`${gateway}/ready`, {
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) throw new Error("not ready");
    return Response.json(
      { status: "ready" },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return errorResponse(503, "API service unavailable");
  }
}
