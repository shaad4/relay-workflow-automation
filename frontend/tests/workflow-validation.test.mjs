import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  workflowDefinition,
  validateCanvas,
  contractOutputFields,
} from "../src/components/workflow/workflowValidation.js";
import { guaranteedPreviousNodesFor } from "../src/components/workflow/workflowVariables.js";

// Use the existing Next compiler; no additional test framework or dependency.
const require = createRequire(import.meta.url);
const { transformSync } = require("next/dist/build/swc");
const cache = new Map();
function component(name) {
  if (cache.has(name)) return cache.get(name);
  const path = new URL(
    `../src/components/workflow/${name}.jsx`,
    import.meta.url,
  );
  const { code } = transformSync(readFileSync(path, "utf8"), {
    filename: path.pathname,
    jsc: {
      parser: { syntax: "ecmascript", jsx: true },
      transform: { react: { runtime: "automatic" } },
    },
    module: { type: "commonjs" },
  });
  const compiledModule = { exports: {} };
  new Function("module", "exports", "require", code)(
    compiledModule,
    compiledModule.exports,
    (id) => (id.startsWith("./") ? component(id.slice(2)) : require(id)),
  );
  cache.set(name, compiledModule.exports);
  return compiledModule.exports;
}
const node = (id, typeId = "ai.generate") => ({
  id: `temp-${id}`,
  position: { x: 1, y: 2 },
  data: { nodeId: id, typeId, label: id, config: {} },
});
const nodes = [node("trigger_1", "trigger.manual"), node("generate_1")];
nodes[1].data.config = {
  connection_id: "{{trigger.data.connection}}",
  model: "model-id",
  prompt: "Report: {{trigger_1.research_topic}}",
};
const edges = [
  { source: nodes[0].id, target: nodes[1].id, data: { condition: "approved" } },
];
const issue = {
  code: "INVALID_EXPRESSION_REFERENCE",
  node_id: "generate_1",
  field: "prompt",
  expression: "{{trigger_1.research_topic}}",
  message: "Unknown expression root 'trigger_1'.",
  suggestion: "Use {{trigger.data.research_topic}}.",
};

test("unsaved canvas reaches shared validation with logical IDs, conditions, and optional sample input", async () => {
  let payload;
  const result = await validateCanvas({
    nodes,
    edges,
    sampleText: '{"research_topic":"RAG"}',
    isCurrent: () => true,
    request: async (body) => {
      payload = body;
      return { valid: false, errors: [issue], warnings: [] };
    },
  });
  assert.deepEqual(
    payload.nodes.find((node) => node.node_id === "generate_1").configuration,
    nodes[1].data.config,
  );
  assert.deepEqual(payload.edges[0], {
    source_node_id: "trigger_1",
    target_node_id: "generate_1",
    condition: "approved",
  });
  assert.deepEqual(payload.sample_input, { research_topic: "RAG" });
  assert.equal(result.errors[0].canvasNodeId, "temp-generate_1");
  assert.equal(result.errors[0].suggestion, issue.suggestion);
  assert.equal("sample_input" in workflowDefinition(nodes, edges), false);
  assert.deepEqual(workflowDefinition(nodes, edges, "{}").sample_input, {});
});

test("stale successes and failures are discarded; invalid samples and unavailable validation never pass", async () => {
  for (const fail of [false, true]) {
    let current = true,
      finish;
    const pending = validateCanvas({
      nodes,
      edges,
      isCurrent: () => current,
      request: () =>
        new Promise((resolve, reject) => {
          finish = () =>
            fail
              ? reject(new Error("offline"))
              : resolve({ valid: true, errors: [], warnings: [] });
        }),
    });
    current = false;
    finish();
    assert.equal(await pending, null);
  }
  for (const sampleText of ["{", "[]", "null", '"text"']) {
    const result = await validateCanvas({
      nodes,
      edges,
      sampleText,
      isCurrent: () => true,
      request: () => assert.fail("Invalid sample must not be submitted"),
    });
    assert.equal(result.errors[0].code, "INVALID_SAMPLE_INPUT");
  }
  for (const response of [{}, { valid: true, errors: [issue], warnings: [] }]) {
    const result = await validateCanvas({
      nodes,
      edges,
      isCurrent: () => true,
      request: async () => response,
    });
    assert.equal(result.isValid, false);
    assert.equal(result.errors[0].code, "VALIDATION_UNAVAILABLE");
  }
});

test("validation dialog shows the node, field, expression, suggestion, warnings and sample controls", () => {
  const Dialog = component("WorkflowValidation").default;
  const markup = renderToStaticMarkup(
    createElement(Dialog, {
      open: true,
      isValid: false,
      errors: [{ ...issue, nodeId: issue.node_id, nodeLabel: "Write report" }],
      warnings: [{ message: "Review provider availability" }],
      onSelectIssue() {},
      onSampleChange() {},
      onValidate() {},
    }),
  );
  for (const text of [
    "Write report → prompt",
    issue.expression,
    issue.suggestion,
    "Review provider availability",
    "Sample trigger input (optional)",
    "Validate again",
  ])
    assert.ok(markup.includes(text), text);
  const stale = renderToStaticMarkup(
    createElement(Dialog, {
      open: true,
      isValid: true,
      needsValidation: true,
      errors: [issue],
    }),
  );
  assert.ok(!stale.includes("passed validation"));
  assert.ok(!stale.includes(issue.suggestion));
});

test("inspector hints and selectable outputs follow the fetched contract", () => {
  const { InspectorValidation, FieldFeedback } = component(
    "InspectorValidation",
  );
  const schema = {
    required: ["prompt"],
    properties: { prompt: { type: "string", maxLength: 123 } },
  };
  const markup = renderToStaticMarkup(
    createElement(
      InspectorValidation.Provider,
      { value: { schema, issues: [issue] } },
      createElement(FieldFeedback, { field: "prompt" }),
    ),
  );
  for (const text of ["Required", "123 characters", issue.suggestion])
    assert.ok(markup.includes(text), text);
  const contract = {
    output_schema: {
      properties: { new_text: { type: "string" }, details: { type: "object" } },
    },
  };
  assert.deepEqual(contractOutputFields(contract), ["new_text", "details"]);
  assert.deepEqual(contractOutputFields(contract, true), ["new_text"]);
});

test("variable picker excludes branch-only and approval outputs at a merge", () => {
  const graph = [
    node("start", "trigger.manual"),
    node("split", "logic.condition"),
    node("left"),
    node("right", "human.approval"),
    node("join"),
  ];
  const links = [
    ["start", "split"],
    ["split", "left"],
    ["split", "right"],
    ["left", "join"],
    ["right", "join"],
  ].map(([a, b]) => ({ source: `temp-${a}`, target: `temp-${b}` }));
  assert.deepEqual(
    guaranteedPreviousNodesFor(graph, links, "temp-join").map(
      (n) => n.data.nodeId,
    ),
    ["split"],
  );
  assert.deepEqual(
    guaranteedPreviousNodesFor(graph, links, "temp-left").map(
      (n) => n.data.nodeId,
    ),
    ["split"],
  );
});
