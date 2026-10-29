import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { deadLetterError, deadLetterMessage } from "../src/lib/deadLetter.js";

const moduleURL = (source) =>
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
process.env.NEXT_PUBLIC_AUTH_API_URL = "https://relay.test";
const client = moduleURL(
  await readFile(new URL("../src/lib/api.js", import.meta.url), "utf8"),
);
const source = await readFile(
  new URL("../src/services/deadLetter.js", import.meta.url),
  "utf8",
);
const service = await import(
  moduleURL(source.replace('"@/lib/api"', JSON.stringify(client)))
);

test("DLQ uses gateway cookies, backend filters, bounded pages, encoded IDs and bodyless mutations", async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return Response.json(
      url.includes("/replay/")
        ? { status: "accepted", execution_id: "new-run" }
        : { items: [], total: 0, limit: 10, offset: 0 },
      { status: url.includes("/replay/") ? 202 : 200 },
    );
  };
  try {
    await service.getDeadLetterEvents();
    await service.getDeadLetterEvents({ status: "pending", offset: 10 });
    await service.getDeadLetterEvent("event/id");
    assert.equal(
      (await service.replayDeadLetterEvent("event/id")).execution_id,
      "new-run",
    );
    await service.resolveDeadLetterEvent("event/id");
    assert.deepEqual(
      calls.map(({ url, options }) => [
        url.replace("https://relay.test", ""),
        options.method,
      ]),
      [
        ["/dead-letter-events/?limit=10&offset=0", "GET"],
        ["/dead-letter-events/?limit=10&offset=10&status=pending", "GET"],
        ["/dead-letter-events/event%2Fid/", "GET"],
        ["/dead-letter-events/event%2Fid/replay/", "POST"],
        ["/dead-letter-events/event%2Fid/resolve/", "POST"],
      ],
    );
    for (const { options } of calls) {
      assert.equal(options.credentials, "include");
      assert.equal(options.body, undefined);
    }
  } finally {
    globalThis.fetch = original;
  }
});

test("backend failures retain status without exposing internal error text to the UI", async () => {
  const original = globalThis.fetch;
  try {
    for (const status of [404, 409, 422, 500, 502, 503, 504]) {
      globalThis.fetch = async () =>
        Response.json(
          { detail: "private stack trace and credentials" },
          { status },
        );
      await assert.rejects(service.replayDeadLetterEvent("event"), (error) => {
        assert.equal(error.status, status);
        assert.doesNotMatch(
          deadLetterError(error),
          /private|stack|credentials/,
        );
        return true;
      });
    }
    assert.match(deadLetterError({ status: 404 }), /not found/);
    assert.match(deadLetterError({ status: 409 }), /already been handled/);
    assert.match(
      deadLetterError({ status: 422 }),
      /not eligible for safe replay/,
    );
  } finally {
    globalThis.fetch = original;
  }
});

test("DLQ keeps existing authentication refresh and cookie handling", async () => {
  const original = globalThis.fetch;
  const originalWindow = globalThis.window;
  const calls = [];
  globalThis.window = { dispatchEvent() {} };
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return calls.length === 1
      ? Response.json({ detail: "Expired" }, { status: 401 })
      : Response.json({ id: "event", status: "pending" });
  };
  try {
    assert.equal((await service.getDeadLetterEvent("event")).id, "event");
    assert.deepEqual(
      calls.map((call) => call.url),
      [
        "https://relay.test/dead-letter-events/event/",
        "https://relay.test/auth/refresh",
        "https://relay.test/dead-letter-events/event/",
      ],
    );
    for (const { options } of calls)
      assert.equal(options.credentials, "include");
  } finally {
    globalThis.fetch = original;
    globalThis.window = originalWindow;
  }
});

test("only bounded safe error messages render, never payloads or diagnostic dumps", () => {
  assert.equal(
    deadLetterMessage({
      message: "Action execution failed",
      payload: { secret: "hidden" },
    }),
    "Action execution failed",
  );
  for (const message of [
    "Authorization: Bearer secret123",
    "api_key=secret123",
    'password="secret123"',
    "Bearer secret123",
    "https://user:secret123@example.test?key=secret123",
  ]) {
    assert.doesNotMatch(deadLetterMessage({ message }), /secret123/);
  }
  for (const message of [
    "Traceback: credentials",
    "Error\n at private.js:12",
    '{"payload":"private"}',
    "-----BEGIN PRIVATE KEY----- secret -----END PRIVATE KEY-----",
  ])
    assert.doesNotMatch(
      deadLetterMessage({ message }),
      /credentials|private|secret/,
    );
  assert.equal(deadLetterMessage({ message: "x".repeat(1000) }).length, 500);
  assert.match(deadLetterMessage(null), /No error message/);
});
