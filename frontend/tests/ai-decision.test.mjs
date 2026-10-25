import test from "node:test";
import assert from "node:assert/strict";
import {
  validateNodeConfiguration,
  validateWorkflowConfiguration,
  validateDecisionReferences,
  normalizeDecisionConfiguration,
  upgradeDecisionConfiguration,
  renameDecisionInput,
} from "../src/components/workflow/configValidation.js";
import {
  outputsByType,
  previousNodesFor,
} from "../src/components/workflow/workflowVariables.js";
import {
  getNodeDefinition,
  clearExampleNodeConfig,
} from "../src/components/workflow/nodeDefinitions.js";
import {
  workflowSaveSnapshot,
  workflowChangedDuringSave,
} from "../src/components/workflow/workflowSaveState.js";

const id = "fea3a93e-187a-4fe3-bb51-386a7f7e938f";
const valid = {
  connection_id: id,
  model: "catalog-model",
  instructions: "Classify the request.\nExplain your choice.",
  input_mappings: {
    message: "{{trigger.data.message}}",
    customer: { tier: "premium", flags: [true, false], amount: 20 },
  },
  rag_context: "{{nodes.policies.context}}",
  allowed_decisions: ["TECHNICAL", "BILLING"],
};
const node = (id, logical, type, config = {}) => ({
  id,
  position: { x: 0, y: 0 },
  data: { nodeId: logical, typeId: type, label: logical, config },
});
const nodes = [
  node("trigger-ui", "webhook", "trigger.webhook", { webhook_id: id }),
  node("rag-ui", "policies", "ai.rag_search", {
    knowledge_base_id: id,
    query: "Policy",
    top_k: 5,
  }),
  node("decision-ui", "classify", "ai.decision", valid),
  node("email-ui", "email", "action.email", {
    connection_id: id,
    to: "test@example.com",
    subject: "Result",
    body: "{{nodes.classify.reason}}",
  }),
];
const edges = [
  { source: "trigger-ui", target: "rag-ui" },
  { source: "rag-ui", target: "decision-ui" },
  { source: "decision-ui", target: "email-ui" },
];
const validate = (patch = {}) =>
  validateNodeConfiguration("ai.decision", { ...valid, ...patch });

test("AI Decision defaults match the backend without provider or outcome assumptions", () => {
  assert.deepEqual(getNodeDefinition("ai.decision").defaultConfig, {
    connection_id: "",
    model: "",
    instructions: "",
    input_mappings: {},
    rag_context: "",
    allowed_decisions: [],
  });
});
test("valid generic config and optional RAG/inputs pass", () => {
  assert.deepEqual(validate(), []);
  assert.deepEqual(validate({ rag_context: "", input_mappings: {} }), []);
  assert.deepEqual(validateWorkflowConfiguration(nodes, edges), []);
});
test("connection and model validation reject missing and malformed selections", () => {
  for (const connection_id of ["", "placeholder", null])
    assert.ok(
      validate({ connection_id }).some(
        (error) => error.field === "connection_id",
      ),
    );
  for (const model of ["", "  ", 5, "x".repeat(151)])
    assert.ok(validate({ model }).some((error) => error.field === "model"));
});
test("multiline instructions preserve whitespace and enforce 10,000 characters", () => {
  for (const instructions of ["", " \n", null, "x".repeat(10001)])
    assert.ok(
      validate({ instructions }).some(
        (error) => error.field === "instructions",
      ),
    );
  assert.deepEqual(validate({ instructions: "x".repeat(10000) }), []);
  assert.equal(
    normalizeDecisionConfiguration(valid).instructions,
    valid.instructions,
  );
});
test("allowed decisions enforce count, identifiers, length and case-insensitive uniqueness", () => {
  for (const allowed_decisions of [
    [],
    ["ONE"],
    Array.from({ length: 21 }, (_, i) => `OUTCOME_${i}`),
    ["ok", "OK"],
    ["A B", "OTHER"],
    ["1BAD", "OTHER"],
    ["A-B", "OTHER"],
    ["a".repeat(101), "OTHER"],
    [null, "OTHER"],
  ]) {
    assert.ok(
      validate({ allowed_decisions }).some(
        (error) => error.field === "allowed_decisions",
      ),
      JSON.stringify(allowed_decisions),
    );
  }
  assert.deepEqual(
    validate({
      allowed_decisions: Array.from({ length: 20 }, (_, i) => `OUTCOME_${i}`),
    }),
    [],
  );
  assert.deepEqual(
    normalizeDecisionConfiguration({
      allowed_decisions: [" qualified ", "follow_up"],
    }).allowed_decisions,
    ["QUALIFIED", "FOLLOW_UP"],
  );
});
test("mapping rename preserves order and nested values without overwriting duplicate keys", () => {
  const original = structuredClone(valid.input_mappings);
  const renamed = renameDecisionInput(original, "message", "request");
  assert.equal(renamed.request, valid.input_mappings.message);
  assert.deepEqual(renamed.customer, original.customer);
  assert.equal(renameDecisionInput(original, "message", "customer"), null);
  assert.equal(renameDecisionInput(original, "message", " customer "), null);
  assert.deepEqual(original, valid.input_mappings);
  assert.ok(
    validate({ input_mappings: { " ": "empty name" } }).some(
      (error) => error.field === "input_mappings",
    ),
  );
  assert.ok(
    validate({ input_mappings: [] }).some(
      (error) => error.field === "input_mappings",
    ),
  );
});
test("picker graph only contains upstream nodes and uses logical IDs", () => {
  assert.deepEqual(
    previousNodesFor(nodes, edges, "decision-ui").map((n) => n.data.nodeId),
    ["policies"],
  );
  assert.ok(
    previousNodesFor(nodes, edges, "email-ui").some(
      (n) => n.data.nodeId === "classify",
    ),
  );
  assert.ok(
    !previousNodesFor(nodes, edges, "rag-ui").some(
      (n) => n.data.nodeId === "classify",
    ),
  );
  assert.deepEqual(outputsByType["ai.decision"], [
    "decision",
    "reason",
    "data",
    "model",
    "input_tokens",
    "output_tokens",
  ]);
  assert.deepEqual(outputsByType["ai.rag_search"], ["chunks", "context"]);
  assert.ok(outputsByType["action.http_request"].includes("body"));
});
test("RAG references survive deletion and are reported as invalid rather than cleared", () => {
  const saved = structuredClone(valid);
  assert.deepEqual(
    validateDecisionReferences(saved, nodes, edges, "decision-ui"),
    [],
  );
  const errors = validateDecisionReferences(
    saved,
    nodes.filter((n) => n.id !== "rag-ui"),
    edges,
    "decision-ui",
  );
  assert.ok(errors.some((error) => error.field === "rag_context"));
  assert.equal(saved.rag_context, "{{nodes.policies.context}}");
  assert.ok(
    validate({ rag_context: "x".repeat(2001) }).some(
      (error) => error.field === "rag_context",
    ),
  );
});
test("multiple upstream RAG references work; downstream and nested missing references fail", () => {
  const extra = node("rag-other", "faq", "ai.rag_search");
  const graph = [
    ...edges,
    { source: "trigger-ui", target: "rag-other" },
    { source: "rag-other", target: "decision-ui" },
  ];
  assert.deepEqual(
    validateDecisionReferences(
      { rag_context: "{{nodes.policies.context}}\n{{nodes.faq.context}}" },
      [...nodes, extra],
      graph,
      "decision-ui",
    ),
    [],
  );
  assert.ok(
    validateDecisionReferences(
      { input_mappings: { nested: [{ value: "{{nodes.email.message_id}}" }] } },
      nodes,
      edges,
      "decision-ui",
    ).length,
  );
  assert.ok(
    validateDecisionReferences(
      { input_mappings: { field: "{{trigger.data.x}}" } },
      nodes,
      [],
      "decision-ui",
    ).length,
  );
});
test("graph cycles cannot expose a node to itself or loop indefinitely", () => {
  const previous = previousNodesFor(
    nodes,
    [...edges, { source: "decision-ui", target: "rag-ui" }],
    "decision-ui",
  );
  assert.ok(!previous.some((n) => n.id === "decision-ui"));
});
test("legacy prompts remain intact until explicit upgrade", () => {
  const legacy = {
    prompt: "Classify incoming customer request priority",
    model: "saved-model",
    inputs: { custom: "data" },
  };
  assert.deepEqual(clearExampleNodeConfig("ai.decision", legacy), legacy);
  assert.ok(
    validateNodeConfiguration("ai.decision", legacy).some(
      (error) => error.field === "legacy",
    ),
  );
  const upgraded = upgradeDecisionConfiguration(legacy);
  assert.equal(upgraded.instructions, legacy.prompt);
  assert.equal(upgraded.model, "saved-model");
  assert.ok(!Object.hasOwn(upgraded, "prompt"));
  assert.ok(Object.hasOwn(legacy, "prompt"));
  assert.equal(
    upgradeDecisionConfiguration({
      ...legacy,
      instructions: "Existing instructions",
    }).instructions,
    "Existing instructions",
  );
});
test("draft save/reload retains model, mappings, instructions and separate RAG context", () => {
  const restored = JSON.parse(workflowSaveSnapshot(nodes, edges)).nodes.find(
    (n) => n.nodeId === "classify",
  ).config;
  assert.deepEqual(restored, valid);
  assert.equal(restored.model, "catalog-model");
  assert.ok(!Object.hasOwn(restored.input_mappings, "rag_context"));
  const edited = nodes.map((n) =>
    n.id === "decision-ui"
      ? {
          ...n,
          data: {
            ...n.data,
            config: { ...valid, instructions: "Updated while saving" },
          },
        }
      : n,
  );
  assert.equal(
    workflowChangedDuringSave(
      workflowSaveSnapshot(nodes, edges),
      { nodes: edited, edges },
      1,
      2,
    ),
    true,
  );
});
test("invalid AI configuration blocks workflow validation with a logical node ID and field", () => {
  const invalid = nodes.map((n) =>
    n.id === "decision-ui"
      ? {
          ...n,
          data: {
            ...n.data,
            config: { ...valid, instructions: "", allowed_decisions: ["ONLY"] },
          },
        }
      : n,
  );
  const errors = validateWorkflowConfiguration(invalid, edges);
  assert.ok(
    errors.some(
      (error) => error.nodeId === "classify" && error.field === "instructions",
    ),
  );
  assert.ok(
    errors.some(
      (error) =>
        error.nodeId === "classify" && error.field === "allowed_decisions",
    ),
  );
});
test("Human Approval and RAG validation remain supported", () => {
  assert.deepEqual(
    validateNodeConfiguration("human.approval", {
      approver_user_id: id,
      message: "Review this",
      timeout_minutes: null,
    }),
    [],
  );
  assert.deepEqual(
    validateNodeConfiguration("ai.rag_search", nodes[1].data.config),
    [],
  );
});
