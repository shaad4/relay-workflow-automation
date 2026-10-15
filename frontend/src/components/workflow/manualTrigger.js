export function validateManualInput(text) {
  let input;
  try { input = JSON.parse(text); }
  catch { return { error: "Enter valid JSON before running this workflow." }; }
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    return { error: "Trigger input must be a JSON object." };
  }
  const bytes = new TextEncoder().encode(JSON.stringify({ input })).length;
  if (bytes > 65536) return { error: "Trigger input is too large. The request must be 65,536 bytes or less." };
  return { input };
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
