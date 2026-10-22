import { apiRequest } from "@/lib/api";

const eventPath = id => `/dead-letter-events/${encodeURIComponent(id)}/`;
function get(endpoint, signal) {
  const timeout = AbortSignal.timeout(15000);
  return apiRequest(endpoint, { method: "GET", signal: signal ? AbortSignal.any([signal, timeout]) : timeout });
}
export function getDeadLetterEvents({ status = "", limit = 10, offset = 0, signal } = {}) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (status) query.set("status", status);
  return get(`/dead-letter-events/?${query}`, signal);
}
export function getDeadLetterEvent(id, { signal } = {}) { return get(eventPath(id), signal); }
// Mutations deliberately have no automatic timeout or retry: a lost response may
// still have committed. Refresh the event before offering another submission.
export function replayDeadLetterEvent(id) { return apiRequest(`${eventPath(id)}replay/`, { method: "POST" }); }
export function resolveDeadLetterEvent(id) { return apiRequest(`${eventPath(id)}resolve/`, { method: "POST" }); }
