import { apiRequest } from "@/lib/api";

export function listConnections() {
  return apiRequest("/connections/", { method: "GET" });
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
