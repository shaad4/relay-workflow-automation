import { apiRequest } from "@/lib/api";

export function listConnections() {
  return apiRequest("/connections/", { method: "GET" });
}

export function startGmailOAuth() {
  const baseUrl = process.env.NEXT_PUBLIC_AUTH_API_URL?.replace(/\/$/, "");
  if (!baseUrl) throw new Error("API URL is not configured");
  return `${baseUrl}/connections/gmail/oauth/start`;
}

export function createConnection(data) {
  return apiRequest("/connections/", { method: "POST", body: JSON.stringify(data) });
}

export function updateConnection(id, data) {
  return apiRequest(`/connections/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteConnection(id) {
  return apiRequest(`/connections/${id}/`, { method: "DELETE" });
}

export function testConnection(id) {
  return apiRequest(`/connections/${id}/test/`, { method: "POST" });
}
