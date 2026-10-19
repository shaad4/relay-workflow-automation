export const executionFilters = [
  ["", "All executions"], ["completed", "Completed"], ["running", "Running"],
  ["failed", "Failed"], ["waiting_for_approval", "Waiting for approval"], ["pending", "Pending"],
];

export function normalizeStatus(status) { return typeof status === "string" ? status.toLowerCase() : "unknown"; }
export function statusLabel(status) {
  const value = normalizeStatus(status);
  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll("_", " ");
}
export function pollingDelay(status) {
  const value = normalizeStatus(status);
  if (value === "pending" || value === "running") return 4000;
  if (value === "waiting_for_approval") return 30000;
  return null;
}
export function workflowName(execution) {
  return execution.workflow_name?.trim() || `Workflow #${execution.workflow_id.slice(0, 8)}`;
}
export function formatDuration(value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "—";
  if (value < 1000) return `${value} ms`;
  if (value < 60000) return `${Math.floor(value / 100) / 10} s`;
  const seconds = Math.floor(value / 1000);
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor(seconds % 3600 / 60)}m`;
}
export function formatTime(value) {
  if (!value || Number.isNaN(new Date(value).getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value));
}
export function executionError(error) {
  if (error?.status === 404) return "This execution could not be found. It may no longer be available in this workspace.";
  if (error?.status === 401) return "Your session has expired. Please sign in again.";
  if (error?.name === "TimeoutError") return "The request took too long. Please try again.";
  return "We couldn’t load execution data. Check your connection and try again.";
}
function invalid() { throw new Error("Unexpected execution response"); }
function optionalText(value) { return value == null || typeof value === "string"; }
function validRecord(item) {
  return item && typeof item === "object" && typeof item.id === "string" && item.id.length > 0 &&
    typeof item.status === "string" && optionalText(item.started_at) && optionalText(item.completed_at) &&
    (item.duration_ms == null || (Number.isFinite(item.duration_ms) && item.duration_ms >= 0));
}
export function validateExecution(item) {
  if (!validRecord(item) || typeof item.workflow_id !== "string" || !optionalText(item.workflow_name) ||
      !optionalText(item.workflow_version_id) || !optionalText(item.trigger_type)) invalid();
  return item;
}
export function validateExecutionList(data) {
  if (!data || !Array.isArray(data.items) || !Number.isInteger(data.total) || data.total < 0 ||
      !Number.isInteger(data.page) || data.page < 1 || !Number.isInteger(data.page_size) || data.page_size < 1) invalid();
  data.items.forEach(validateExecution);
  return data;
}
export function validateExecutionSteps(data) {
  if (!data || !Array.isArray(data.items)) invalid();
  for (const step of data.items) {
    if (!validRecord(step) || typeof step.node_id !== "string" || !optionalText(step.node_name) ||
        !optionalText(step.node_type) || !Number.isInteger(step.sequence) || step.sequence < 1 ||
        !Number.isInteger(step.attempt) || step.attempt < 1) invalid();
  }
  return { ...data, items: [...data.items].sort((a, b) => a.sequence - b.sequence || a.attempt - b.attempt || a.id.localeCompare(b.id)) };
}
