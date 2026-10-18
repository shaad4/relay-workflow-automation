import { test } from "node:test";
import assert from "node:assert/strict";
import { validateManualInput, manualRunError, hasManualTrigger, loadManualTrigger } from "../src/components/workflow/manualTrigger.js";

test("accepts a JSON object, including empty input", () => {
  assert.deepEqual(validateManualInput("{}"), { input: {}, bytes: 12 });
  assert.deepEqual(validateManualInput('{"order_id":"ORD-TEST-187"}').input, { order_id: "ORD-TEST-187" });
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


test("detects manual triggers in API and canvas nodes without matching other triggers", () => {
  assert.equal(hasManualTrigger([{ node_type: "trigger.manual" }]), true);
  assert.equal(hasManualTrigger({ nodes: [{ type: "trigger.manual" }] }), true);
  assert.equal(hasManualTrigger([{ type: "workflowNode", data: { typeId: "trigger.manual" } }]), true);
  for (const type of ["trigger.webhook", "trigger.schedule", "human.approval"]) {
    assert.equal(hasManualTrigger([{ node_type: type }]), false);
  }
  assert.equal(hasManualTrigger([]), false);
});

test("run availability checks the published version even when a newer manual draft exists", async () => {
  const versions = [{ id: "draft", version: 3 }, { id: "published", version: 2 }];
  const calls = [];
  const operations = {
    getWorkflowVersions: async () => versions,
    getWorkflowNodes: async (id, version) => {
      calls.push([id, version]);
      return [{ node_type: version === 3 ? "trigger.manual" : "trigger.webhook" }];
    },
  };
  assert.deepEqual(await loadManualTrigger({ workflowId: "wf", publishedVersionId: "published" }, operations), { hasManualTrigger: false, versionNumber: 2 });
  assert.deepEqual(calls, [["wf", 2]]);
  assert.deepEqual(await loadManualTrigger({ workflowId: "wf", versions }, operations), { hasManualTrigger: true, versionNumber: 3 });
});

test("manual published workflows are recognized and missing published versions do not fall back to drafts", async () => {
  const versions = [{ id: "published", version_number: 1 }];
  const operations = {
    getWorkflowVersions: async () => ({ versions }),
    getWorkflowNodes: async () => ({ nodes: [{ node_type: "trigger.manual" }] }),
  };
  assert.deepEqual(await loadManualTrigger({ workflowId: "wf", publishedVersionId: "published" }, operations), { hasManualTrigger: true, versionNumber: 1 });
  assert.deepEqual(await loadManualTrigger({ workflowId: "wf", publishedVersionId: "missing" }, operations), { hasManualTrigger: false });
  await assert.rejects(loadManualTrigger({ workflowId: "wf", versions }, { getWorkflowNodes: async () => { throw Error("offline"); } }), /offline/);
});
