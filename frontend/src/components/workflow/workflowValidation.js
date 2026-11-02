import { workflowSaveSnapshot } from "./workflowSaveState.js";

// Use the same normalization and logical IDs as saving, including unsaved nodes.
export function workflowDefinition(nodes, edges, sampleText = "") {
  const snapshot = JSON.parse(workflowSaveSnapshot(nodes, edges));
  const definition = {
    nodes: snapshot.nodes.map((node) => ({
      node_id: node.nodeId,
      node_type: node.type,
      label: node.label,
      position_x: node.x,
      position_y: node.y,
      configuration: node.config,
    })),
    edges: snapshot.edges.map((edge) => ({
      source_node_id: edge.source,
      target_node_id: edge.target,
      condition: edge.condition,
    })),
  };
  if (sampleText.trim()) {
    let sample;
    try {
      sample = JSON.parse(sampleText);
    } catch {
      throw new Error("Sample trigger input must be a valid JSON object.");
    }
    if (!sample || typeof sample !== "object" || Array.isArray(sample))
      throw new Error("Sample trigger input must be a JSON object.");
    definition.sample_input = sample;
  }
  return definition;
}

export function normalizeValidation(response, nodes) {
  if (
    typeof response?.valid !== "boolean" ||
    !Array.isArray(response.errors) ||
    !Array.isArray(response.warnings) ||
    (response.valid && response.errors.length)
  )
    throw new Error("Invalid validation response.");
  const normalize = (issue) => {
    const nodeId = issue.node_id ?? issue.nodeId;
    const node = nodes.find(
      (item) => (item.data?.nodeId ?? item.id) === nodeId,
    );
    return {
      ...issue,
      nodeId,
      canvasNodeId: node?.id,
      nodeLabel: node?.data?.label || nodeId,
    };
  };
  return {
    isValid: response.valid,
    errors: response.errors.map(normalize),
    warnings: response.warnings.map(normalize),
  };
}

export const validationUnavailable = () => ({
  isValid: false,
  errors: [
    {
      code: "VALIDATION_UNAVAILABLE",
      message:
        "Unable to validate this workflow. Check your connection and retry validation.",
    },
  ],
  warnings: [],
});

// Both explicit validation and inline validation discard stale successes AND failures.
export async function validateCanvas({
  nodes,
  edges,
  sampleText,
  request,
  isCurrent,
}) {
  let definition;
  try {
    definition = workflowDefinition(nodes, edges, sampleText);
  } catch (error) {
    return isCurrent()
      ? {
          isValid: false,
          errors: [
            {
              code: "INVALID_SAMPLE_INPUT",
              field: "sample_input",
              message: error.message,
            },
          ],
          warnings: [],
        }
      : null;
  }
  try {
    const response = await request(definition);
    return isCurrent() ? normalizeValidation(response, nodes) : null;
  } catch {
    return isCurrent() ? validationUnavailable() : null;
  }
}

export function contractFor(catalog, type) {
  return catalog?.nodes?.find((node) => node.node_type === type);
}

export function contractOutputFields(contract, scalarOnly = false) {
  return Object.entries(contract?.output_schema?.properties ?? {})
    .filter(
      ([, schema]) =>
        !scalarOnly ||
        ["string", "integer", "number", "boolean"].includes(schema.type),
    )
    .map(([name]) => name);
}
