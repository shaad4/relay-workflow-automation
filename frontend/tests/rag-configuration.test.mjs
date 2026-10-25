import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeRAGConfiguration,
  ragKnowledgeBaseId,
  validateNodeConfiguration,
  validateWorkflowConfiguration,
} from "../src/components/workflow/configValidation.js";
import {
  getNodeDefinition,
  clearExampleNodeConfig,
} from "../src/components/workflow/nodeDefinitions.js";

const id = "fea3a93e-187a-4fe3-bb51-386a7f7e938f";
const valid = { knowledge_base_id: id, query: "Refund policy?", top_k: 5 };
const errors = (config) => validateNodeConfiguration("ai.rag_search", config);

test("new RAG nodes use canonical empty defaults", () => {
  assert.deepEqual(getNodeDefinition("ai.rag_search").defaultConfig, {
    knowledge_base_id: "",
    query: "",
    top_k: 5,
  });
});
test("strict Top-K boundaries and malformed values", () => {
  for (const top_k of [1, 5, 20])
    assert.deepEqual(errors({ ...valid, top_k }), []);
  for (const top_k of [
    0,
    21,
    1.5,
    "",
    "5",
    "5x",
    "1.5",
    null,
    undefined,
    NaN,
    Infinity,
    true,
  ]) {
    assert.ok(
      errors({ ...valid, top_k }).some((error) => error.field === "top_k"),
      String(top_k),
    );
  }
});
test("static, dynamic and mixed queries retain exact text across JSON persistence", () => {
  for (const query of [
    "Refund policy?",
    "{{trigger.data.customer_message}}",
    "Find policy:\n{{trigger.data.customer_message}}",
    "{{nodes.http_request_1.body}}",
    "x".repeat(2000),
  ]) {
    const reloaded = JSON.parse(
      JSON.stringify(normalizeRAGConfiguration({ ...valid, query })),
    );
    assert.equal(reloaded.query, query);
    assert.deepEqual(errors(reloaded), []);
  }
  for (const query of ["", " \n ", "x".repeat(2001), 42, {}, null])
    assert.ok(
      errors({ ...valid, query }).some((error) => error.field === "query"),
    );
});
test("legacy IDs normalize without mutating original published snapshots", () => {
  const legacy = Object.freeze({
    knowledge_base: id,
    query: "Question",
    top_k: 5,
    workspace_id: "obsolete",
  });
  assert.equal(ragKnowledgeBaseId(legacy), id);
  assert.deepEqual(errors(legacy), []);
  const canonical = normalizeRAGConfiguration(legacy);
  assert.deepEqual(canonical, {
    knowledge_base_id: id,
    query: "Question",
    top_k: 5,
  });
  assert.equal(legacy.knowledge_base, id);
  assert.equal(legacy.workspace_id, "obsolete");
  assert.deepEqual(normalizeRAGConfiguration(canonical), canonical);
});
test("conflicts survive normalization until explicit selection; canonical key takes precedence", () => {
  const conflict = { ...valid, knowledge_base: "another-value" };
  assert.equal(ragKnowledgeBaseId(conflict), id);
  assert.ok(
    errors(normalizeRAGConfiguration(conflict)).some(
      (error) => error.field === "knowledge_base_id",
    ),
  );
  assert.equal(ragKnowledgeBaseId({ ...conflict, knowledge_base_id: "" }), "");
  assert.equal(
    normalizeRAGConfiguration({ ...valid, knowledge_base: id }).knowledge_base,
    undefined,
  );
});
test("unavailable IDs and old placeholders are preserved, never invented or silently cleared", () => {
  const old = {
    knowledge_base: "kb_customer_docs",
    query: "{{input.message}}",
    top_k: 5,
  };
  assert.deepEqual(clearExampleNodeConfig("ai.rag_search", old), old);
  assert.equal(
    normalizeRAGConfiguration(old).knowledge_base_id,
    old.knowledge_base,
  );
  assert.ok(errors(old).some((error) => error.field === "knowledge_base_id"));
  assert.equal(normalizeRAGConfiguration(valid).knowledge_base_id, id);
  for (const knowledge_base_id of ["", 123, null, "not-a-uuid"])
    assert.ok(errors({ ...valid, knowledge_base_id }).length);
});
test("workflow errors associate logical node ID and field", () => {
  const result = validateWorkflowConfiguration(
    [
      {
        id: "react-flow-uuid",
        data: {
          nodeId: "rag_search_7",
          typeId: "ai.rag_search",
          config: { ...valid, top_k: 0 },
        },
      },
    ],
    [],
    { includeStructure: false },
  );
  assert.equal(result[0].nodeId, "rag_search_7");
  assert.equal(result[0].field, "top_k");
});
test("representative existing node configurations remain valid", () => {
  for (const [type, config] of [
    ["trigger.webhook", { webhook_id: id }],
    [
      "action.http_request",
      { connection_id: id, method: "GET", url: "/orders" },
    ],
    [
      "action.email",
      {
        connection_id: id,
        to: "user@example.com",
        subject: "Hello",
        body: "Message",
      },
    ],
    [
      "action.refund",
      { connection_id: id, payment_id: "payment", amount: "5" },
    ],
    [
      "human.approval",
      { approver_user_id: id, message: "Approve?", timeout_minutes: 5 },
    ],
  ])
    assert.deepEqual(validateNodeConfiguration(type, config), []);
});

test("null and empty aliases cannot silently override a valid identifier", () => {
  for (const conflict of [
    { ...valid, knowledge_base: null },
    { ...valid, knowledge_base: "" },
    { ...valid, knowledge_base_id: null, knowledge_base: id },
    { ...valid, knowledge_base_id: "", knowledge_base: id },
  ])
    assert.ok(
      errors(conflict).some((error) => error.field === "knowledge_base_id"),
    );
});
