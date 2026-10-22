import { apiRequest } from "@/lib/api";
import { validateExecution, validateExecutionList, validateExecutionSteps } from "@/lib/executions";

// Keep session restoration and cookie handling in the shared API client.
function request(endpoint, signal) {
  const timeout = AbortSignal.timeout(15000);
  return apiRequest(endpoint, {
    method: "GET",
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
}

export async function getExecutions({ page = 1, pageSize = 10, status = "", signal } = {}) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (status) query.set("status", status.toLowerCase());
  return validateExecutionList(await request(`/executions/?${query}`, signal));
}

export async function getExecutionDetails(executionId, { signal } = {}) {
  return validateExecution(await request(`/executions/${encodeURIComponent(executionId)}/`, signal));
}

/**
 * @typedef {Object} ExecutionStepPayloads
 * @property {unknown|null} input Sanitized input recorded by the API.
 * @property {unknown|null} output Sanitized output recorded by the API.
 * @property {unknown|null} error Sanitized error recorded by the API.
 * Missing fields on older records are presented as empty, without coercing falsy values.
 */
export async function getExecutionSteps(executionId, { signal } = {}) {
  return validateExecutionSteps(await request(`/executions/${encodeURIComponent(executionId)}/steps/`, signal));
}

export async function getExecutionGroups({ page = 1, pageSize = 10, status = "", signal } = {}) {
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize), group_replays: "true" });
  if (status) query.set("status", status.toLowerCase());
  const data = validateExecutionList(await request(`/executions/?${query}`, signal));
  if (data.items.some(item => typeof item.execution_group_id !== "string" || !Number.isInteger(item.attempt_count) || item.attempt_count < 1)) {
    throw new Error("Unexpected execution group response");
  }
  return data;
}

export async function getExecutionAttempts(executionId, { page = 1, signal } = {}) {
  const query = new URLSearchParams({ page: String(page), page_size: "10", group_id: executionId });
  return validateExecutionList(await request(`/executions/?${query}`, signal));
}
