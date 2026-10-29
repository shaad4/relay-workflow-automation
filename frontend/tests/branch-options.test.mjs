import test from "node:test";
import assert from "node:assert/strict";
import { branchOptions } from "../src/components/workflow/branchOptions.js";
import { validateConditionBranches } from "../src/components/workflow/configValidation.js";

const approval = { id: "approval", data: { typeId: "human.approval" } };
const decision = {
  id: "decision-ui",
  data: {
    nodeId: "classify",
    typeId: "ai.decision",
    config: { allowed_decisions: ["BILLING", "TECHNICAL"] },
  },
};
const condition = {
  id: "condition",
  data: {
    typeId: "logic.condition",
    config: { value: "{{nodes.classify.decision}}" },
  },
};
const incoming = { id: "incoming", source: decision.id, target: condition.id };
const branch = (id, source, value) => ({
  id,
  source,
  target: id,
  data: { condition: value },
});

test("approval choices store the exact decisions expected by execution", () => {
  assert.deepEqual(
    branchOptions(approval).map((option) => option.value),
    ["approved", "rejected"],
  );
  assert.equal(
    validateConditionBranches(
      [approval],
      [branch("next", approval.id, "Approved")],
    ).length,
    1,
  );
  assert.equal(
    validateConditionBranches([approval], [branch("next", approval.id, null)])
      .length,
    1,
  );
  assert.equal(
    validateConditionBranches(
      [approval],
      [
        branch("one", approval.id, "approved"),
        branch("two", approval.id, "approved"),
      ],
    ).length,
    2,
  );
});

test("condition choices follow the referenced upstream AI decisions and detect removed outcomes", () => {
  const nodes = [decision, condition];
  const edges = [incoming, branch("next", condition.id, "BILLING")];
  assert.deepEqual(
    branchOptions(condition, nodes, edges).map((option) => option.value),
    ["BILLING", "TECHNICAL"],
  );
  const changed = {
    ...decision,
    data: {
      ...decision.data,
      config: { allowed_decisions: ["GENERAL", "TECHNICAL"] },
    },
  };
  assert.deepEqual(
    branchOptions(condition, [changed, condition], edges).map(
      (option) => option.value,
    ),
    ["GENERAL", "TECHNICAL"],
  );
  assert.equal(
    validateConditionBranches([changed, condition], edges)[0].edgeId,
    "next",
  );
  assert.equal(branchOptions(condition, nodes, []), null);
});

test("literal and boolean condition outputs have exact choices; arbitrary data retains manual input", () => {
  const literal = {
    ...condition,
    data: { ...condition.data, config: { value: " Paid " } },
  };
  assert.deepEqual(branchOptions(literal), [{ value: "Paid", label: "Paid" }]);
  const http = {
    ...decision,
    data: { ...decision.data, typeId: "action.http_request" },
  };
  const success = {
    ...condition,
    data: {
      ...condition.data,
      config: { value: "{{ nodes.classify.success }}" },
    },
  };
  assert.deepEqual(
    branchOptions(success, [http, success], [incoming]).map(
      (option) => option.value,
    ),
    ["true", "false"],
  );
  const dynamic = {
    ...condition,
    data: { ...condition.data, config: { value: "{{trigger.body.category}}" } },
  };
  assert.equal(branchOptions(dynamic), null);
  assert.deepEqual(
    branchOptions({
      ...condition,
      data: { ...condition.data, config: { value: "" } },
    }),
    [],
  );
});
