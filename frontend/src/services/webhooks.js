import { apiRequest } from "@/lib/api";

export function listWebhooks() { return apiRequest("/webhooks/", { method: "GET" }); }
export function getWebhook(id) { return apiRequest(`/webhooks/${id}/`, { method: "GET" }); }
export function createWebhook(data) { return apiRequest("/webhooks/", { method: "POST", body: JSON.stringify(data) }); }
export function updateWebhook(id, data) { return apiRequest(`/webhooks/${id}/`, { method: "PATCH", body: JSON.stringify(data) }); }
export function deleteWebhook(id) { return apiRequest(`/webhooks/${id}/`, { method: "DELETE" }); }
export function regenerateWebhookToken(id) { return apiRequest(`/webhooks/${id}/regenerate-token/`, { method: "POST" }); }

export function getWebhookEndpoint(token) {
  const base = process.env.NEXT_PUBLIC_AUTH_API_URL?.replace(/\/$/, "") || "";
  return `${base}/hooks/${token}`;
}

export function getWebhookTestEndpoint(token) {
  return `${getWebhookEndpoint(token)}/test`;
}

export function startWebhookTestSession(webhookId) {
  return apiRequest(`/webhooks/${webhookId}/test-sessions/`, { method: "POST" });
}

export function getWebhookTestSession(webhookId, sessionId) {
  return apiRequest(`/webhooks/${webhookId}/test-sessions/${sessionId}/`, { method: "GET" });
}
