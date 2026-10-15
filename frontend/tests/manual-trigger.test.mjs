import { test } from "node:test";
import assert from "node:assert/strict";
import { validateManualInput, manualRunError } from "../src/components/workflow/manualTrigger.js";

test("accepts a JSON object, including empty input", () => {
  assert.deepEqual(validateManualInput("{}"), { input: {} });
  assert.deepEqual(validateManualInput('{"order_id":"ORD-TEST-187"}'), { input: { order_id: "ORD-TEST-187" } });
});

test("rejects malformed and non-object JSON", () => {
  assert.match(validateManualInput("{").error, /valid JSON/);
  for (const value of ["[]", "null", '"text"', "42", "true"]) assert.match(validateManualInput(value).error, /JSON object/);
});

test("checks UTF-8 size of the wrapped request", () => {
  assert.match(validateManualInput(JSON.stringify({ data: "🙂".repeat(16384) })).error, /too large/);
  assert.deepEqual(validateManualInput(JSON.stringify({ data: "🙂".repeat(100) })).input.data.length, 200);
});

test("explains uncertain timeout and dispatch failures", () => {
  assert.match(manualRunError({ status: 504 }), /retrying may start another execution/);
  assert.match(manualRunError({ status: 503 }), /unavailable/);
  assert.match(manualRunError({ status: 401 }), /session/);
  assert.match(manualRunError({ status: 409 }), /Manual Trigger/);
  assert.match(manualRunError({ status: 422 }), /JSON input/);
});
