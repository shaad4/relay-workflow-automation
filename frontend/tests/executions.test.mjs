import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  formatDuration, formatTime, normalizeStatus, pollingDelay, statusLabel, workflowName,
  validateExecutionList, validateExecutionSteps, executionError,
} from "../src/lib/executions.js";

const execution = { id: "run-1", workflow_id: "abcdefgh-1234", workflow_name: "Order processing", status: "completed" };
const step = { id: "step-1", node_id: "node-1", node_name: "Search", node_type: "ai.rag_search", status: "completed", sequence: 1, attempt: 1 };

test("names use snapshots and old records have an ID fallback", () => {
  assert.equal(workflowName(execution), "Order processing");
  assert.equal(workflowName({ ...execution, workflow_name: null }), "Workflow #abcdefgh");
  assert.equal(workflowName({ ...execution, workflow_name: "  " }), "Workflow #abcdefgh");
});

test("polls active states, slows approval waits, and stops terminal or unknown states", () => {
  assert.equal(pollingDelay("RUNNING"), 4000);
  assert.equal(pollingDelay("pending"), 4000);
  assert.equal(pollingDelay("WAITING_FOR_APPROVAL"), 30000);
  for (const status of ["COMPLETED", "FAILED", "CANCELLED", "DEAD_LETTERED", "new_state", null]) {
    assert.equal(pollingDelay(status), null);
  }
  assert.equal(normalizeStatus(null), "unknown");
  assert.equal(statusLabel("WAITING_FOR_APPROVAL"), "Waiting for approval");
});

test("durations distinguish missing values from zero and handle boundaries", () => {
  for (const value of [null, undefined, -1, Infinity, "10"]) assert.equal(formatDuration(value), "—");
  assert.equal(formatDuration(0), "0 ms");
  assert.equal(formatDuration(1250), "1.2 s");
  assert.equal(formatDuration(59999), "59.9 s");
  assert.equal(formatDuration(60000), "1m 0s");
  assert.equal(formatDuration(3660000), "1h 1m");
  assert.equal(formatTime(null), "—");
  assert.equal(formatTime("invalid"), "—");
});

test("list validation accepts empty and partial final pages and rejects invalid payloads", () => {
  assert.equal(validateExecutionList({ items: [], total: 0, page: 1, page_size: 10 }).total, 0);
  assert.equal(validateExecutionList({ items: [execution], total: 11, page: 2, page_size: 10 }).items.length, 1);
  for (const data of [null, {}, { items: "bad" }, { items: [null], total: 1, page: 1, page_size: 10 },
    { items: [{ ...execution, workflow_name: {} }], total: 1, page: 1, page_size: 10 },
    { items: [], total: -1, page: 1, page_size: 10 }]) assert.throws(() => validateExecutionList(data));
});

test("step ordering preserves API names and sorts sequence then attempts without mutation", () => {
  const original = [{ ...step, id: "third", sequence: 2 }, { ...step, id: "second", attempt: 2 }, step];
  const result = validateExecutionSteps({ items: original });
  assert.deepEqual(result.items.map(item => item.id), ["step-1", "second", "third"]);
  assert.equal(original[0].id, "third");
  assert.equal(result.items[0].node_name, "Search");
  assert.equal(result.items[0].node_type, "ai.rag_search");
  for (const item of [{ ...step, sequence: 0 }, { ...step, node_type: {} }, { ...step, attempt: null }]) {
    assert.throws(() => validateExecutionSteps({ items: [item] }));
  }
});

test("request error messages never leak backend exception details", () => {
  assert.match(executionError({ status: 404 }), /could not be found/);
  assert.match(executionError({ status: 401 }), /session/);
  assert.match(executionError({ name: "TimeoutError" }), /too long/);
  assert.doesNotMatch(executionError(new Error("secret backend credentials")), /secret|credentials/);
});

test("execution API uses authenticated shared requests, supported filters, encoded IDs, and abort signals", async () => {
  // Import the actual service with only its alias imports resolved for Node's test runner.
  const calls = [];
  globalThis.__executionApiTest = async (...args) => {
    calls.push(args);
    if (args[0].includes("/steps/")) return { items: [step] };
    if (args[0].includes("?")) return { items: [execution], total: 1, page: 2, page_size: 10 };
    return execution;
  };
  const source = (await readFile(new URL("../src/services/executions.js", import.meta.url), "utf8"))
    .replace('import { apiRequest } from "@/lib/api";', 'const apiRequest = (...args) => globalThis.__executionApiTest(...args);')
    .replace('"@/lib/executions"', JSON.stringify(new URL("../src/lib/executions.js", import.meta.url).href));
  const api = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
  try {
    const controller = new AbortController();
    await api.getExecutions({ page: 2, status: "COMPLETED", signal: controller.signal });
    assert.equal(calls[0][0], "/executions/?page=2&page_size=10&status=completed");
    assert.equal(calls[0][1].method, "GET");
    assert.equal(calls[0][1].signal.aborted, false);
    controller.abort();
    assert.equal(calls[0][1].signal.aborted, true);
    await api.getExecutionDetails("id/with space");
    assert.equal(calls[1][0], "/executions/id%2Fwith%20space/");
    await api.getExecutionSteps("id/with space");
    assert.equal(calls[2][0], "/executions/id%2Fwith%20space/steps/");
    await api.getExecutions();
    assert.equal(calls[3][0], "/executions/?page=1&page_size=10");
  } finally { delete globalThis.__executionApiTest; }
});
