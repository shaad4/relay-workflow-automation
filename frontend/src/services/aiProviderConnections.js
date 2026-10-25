import { apiRequest } from "@/lib/api";

const path = (id) => `/ai/connections/${encodeURIComponent(id)}/`;

export function createAIConnection(data) {
  return apiRequest("/ai/connections/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
export function listAIConnections() {
  return apiRequest("/ai/connections/", { method: "GET" });
}
export function getAIConnection(id) {
  return apiRequest(path(id), { method: "GET" });
}
export function updateAIConnection(id, data) {
  return apiRequest(path(id), { method: "PATCH", body: JSON.stringify(data) });
}
export function deleteAIConnection(id) {
  return apiRequest(path(id), { method: "DELETE" });
}
export function testAIConnection(id) {
  return apiRequest(`${path(id)}test/`, { method: "POST" });
}
export function listAIConnectionModels(id) {
  return apiRequest(`${path(id)}models/`, { method: "GET" });
}
