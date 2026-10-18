export function validateManualInput(text) {
  let input;
  try { input = JSON.parse(text); }
  catch { return { error: "Enter valid JSON before running this workflow." }; }
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    return { error: "Trigger input must be a JSON object." };
  }
  const bytes = new TextEncoder().encode(JSON.stringify({ input })).length;
  if (bytes > 65536) return { error: "Trigger input is too large. The request must be 65,536 bytes or less." };
  return { input, bytes };
}

export function manualRunError(error) {
  switch (error?.status) {
    case 401: return "Your session has expired. Sign in and try again.";
    case 404: return "Workflow or published version was not found.";
    case 409: return error.message || "This workflow is inactive or its published version does not contain a Manual Trigger.";
    case 413: return "Trigger input is too large. The request must be 65,536 bytes or less.";
    case 415: return "The server rejected the request format. Please try again.";
    case 422: return error.message || "The server rejected the JSON input.";
    case 503: return "The workflow service is unavailable. Please try again later.";
    case 504: return "The request timed out. Execution status is uncertain; retrying may start another execution.";
    default: return "The connection was interrupted or the request failed. Execution status may be uncertain; retrying may start another execution.";
  }
}


export function hasManualTrigger(raw) {
  const nodes = Array.isArray(raw) ? raw : raw?.nodes ?? raw?.results ?? raw?.data ?? [];
  return Array.isArray(nodes) && nodes.some((node) =>
    (node.node_type ?? node.type ?? node.data?.typeId) === "trigger.manual" || node.data?.typeId === "trigger.manual"
  );
}

export async function loadManualTrigger({ workflowId, publishedVersionId, versions }, { getWorkflowVersions, getWorkflowNodes }) {
  const raw = versions ?? await getWorkflowVersions(workflowId);
  const rows = Array.isArray(raw) ? raw : raw?.versions ?? raw?.results ?? raw?.data ?? [];
  const version = publishedVersionId
    ? rows.find((item) => String(item.id) === String(publishedVersionId))
    : [...rows].sort((a, b) => Number(b.version_number ?? b.version) - Number(a.version_number ?? a.version))[0];
  const versionNumber = version?.version_number ?? version?.version;
  if (versionNumber == null) return { hasManualTrigger: false };
  const nodes = await getWorkflowNodes(workflowId, versionNumber);
  return { hasManualTrigger: hasManualTrigger(nodes), versionNumber };
}
