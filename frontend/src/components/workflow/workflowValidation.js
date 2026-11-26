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


// Publication can reject a draft even after a successful preflight (for example,
// if another editor changed the saved definition). Keep the server's field issues.
export function publicationValidation(error, nodes) {
  if (
    error?.status !== 400 ||
    error.detail?.code !== "WORKFLOW_VALIDATION_FAILED"
  )
    return null;
  try {
    const result = normalizeValidation(error.detail, nodes);
    return result.isValid ? null : result;
  } catch {
    return null;
  }
}

const actionProviders = {
  "action.email": "gmail",
  "action.http_request": "http",
  "action.refund": "stripe",
};

// Check saved connection membership and provider compatibility without sending
// a test email, making a payment, or exposing credentials.
export async function validateAppConnections(nodes, listConnections) {
  const actions = nodes.filter(
    (node) =>
      Object.hasOwn(actionProviders, node.data?.typeId) &&
      !/^\{\{\s*[^{}]+\s*\}\}$/.test(
        String(node.data.config?.connection_id ?? ""),
      ),
  );
  if (!actions.length) return [];
  try {
    const connections = await listConnections();
    if (!Array.isArray(connections))
      throw new Error("Invalid app connection list");
    return actions
      .filter((node) => {
        const provider = actionProviders[node.data.typeId];
        const connection = connections.find(
          (item) => item.id === node.data.config?.connection_id,
        );
        return !connection || connection.provider !== provider;
      })
      .map((node) => ({
        code: "NODE_CONFIG_CONNECTION_ID",
        node_id: node.data.nodeId ?? node.id,
        field: "connection_id",
        message: `${node.data.label || "Action"}: Choose a saved ${actionProviders[node.data.typeId]} connection before publishing.`,
      }));
  } catch {
    return [
      {
        code: "APP_CONNECTION_CHECK_FAILED",
        message:
          "Unable to verify app connections. Retry validation before publishing.",
      },
    ];
  }
}
