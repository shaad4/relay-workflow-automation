import { test } from "node:test";
import assert from "node:assert/strict";
import {
  defaultPayloadTab,
  emptyPayloadMessages,
  payloadSection,
  serializePayload,
  PAYLOAD_SECTION_SIZE,
} from "../src/lib/executionPayload.js";
import { validateExecutionSteps } from "../src/lib/executions.js";

test("payload defaults follow execution transitions", () => {
  for (const status of [
    "pending",
    "running",
    "waiting_for_approval",
    "unknown",
  ])
    assert.equal(defaultPayloadTab(status), "input");
  assert.equal(defaultPayloadTab("COMPLETED"), "output");
  assert.equal(defaultPayloadTab("failed"), "error");
  assert.equal(defaultPayloadTab("DEAD_LETTERED"), "error");
});

test("JSON serialization preserves primitives, nested null, arrays, redactions and unsafe text", () => {
  const values = [
    false,
    0,
    "",
    "line one\nline two",
    [],
    {},
    null,
    {
      secret: "[REDACTED]",
      html: '<script>alert("x")</script>',
      nested: [null, false, "🙂"],
    },
  ];
  for (const value of values)
    assert.deepEqual(JSON.parse(serializePayload(value)), value);
  assert.equal(serializePayload({ input: 1 }), '{\n  "input": 1\n}');
  assert.equal(serializePayload(undefined), "null");
  assert.equal(emptyPayloadMessages.input, "No input data recorded.");
  assert.equal(emptyPayloadMessages.output, "No output available.");
  assert.equal(emptyPayloadMessages.error, "No error recorded.");
});

test("large prompt sections are bounded, lossless, and do not break emoji", () => {
  const text = serializePayload({
    context: "Long RAG document 🙂\n".repeat(10000),
  });
  const first = payloadSection(text);
  assert.ok(first.total > 1);
  let reassembled = "";
  for (let page = 0; page < first.total; page++) {
    const section = payloadSection(text, page);
    assert.ok(section.text.length <= PAYLOAD_SECTION_SIZE + 1);
    assert.equal(
      section.text,
      Buffer.from(section.text, "utf8").toString("utf8"),
    );
    reassembled += section.text;
  }
  assert.equal(reassembled, text);
  assert.equal(payloadSection(text, 999999).page, first.total - 1);
  assert.equal(payloadSection(text, -1).page, 0);
  assert.equal(payloadSection("x".repeat(PAYLOAD_SECTION_SIZE)).total, 1);
});

test("step validation retains all payload types and old records without extra requests or coercion", () => {
  const base = {
    id: "step",
    node_id: "node",
    status: "completed",
    sequence: 1,
    attempt: 1,
  };
  const payloads = [
    {
      input: { headers: { authorization: "[REDACTED]" } },
      output: { received: true },
      error: null,
    },
    {
      input: { query: "policy" },
      output: [{ content: "Long context".repeat(5000) }],
      error: null,
    },
    { input: { amount: 300 }, output: { decision: "REJECT" }, error: null },
    { input: true, output: false, error: null },
    {
      input: "Write an email",
      output: "Dear customer,\nYour request was reviewed.",
      error: null,
    },
    {
      input: { to: "test@example.com" },
      output: null,
      error: { message: "Delivery failed", code: 502 },
    },
    { input: 0, output: "", error: [] },
    {},
  ];
  for (const payload of payloads) {
    const original = { ...base, ...payload };
    assert.deepEqual(
      validateExecutionSteps({ items: [original] }).items[0],
      original,
    );
  }
});

test("syntax colors preserve exact JSON including section boundaries within strings", async () => {
  const { payloadTokens } = await import("../src/lib/executionPayload.js");
  const text = serializePayload({
    prompt: 'Line one\n"quoted" <script> [REDACTED]',
    count: 2.5,
    enabled: false,
    missing: null,
  });
  const tokens = payloadTokens(text);
  assert.equal(tokens.map((token) => token.text).join(""), text);
  for (const type of ["key", "string", "number", "boolean", "null"])
    assert.ok(tokens.some((token) => token.type === type));
  const start = text.indexOf("Line") + 2;
  const end = text.indexOf("quoted") + 3;
  const partial = payloadTokens(text, start, end);
  assert.equal(
    partial.map((token) => token.text).join(""),
    text.slice(start, end),
  );
  assert.equal(partial[0].type, "string");
});
