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

export async function getExecutionSteps(executionId, { signal } = {}) {
  return validateExecutionSteps(await request(`/executions/${encodeURIComponent(executionId)}/steps/`, signal));
}
