import { apiRequest } from "@/lib/api";

export function listKnowledgeBases() {
  return apiRequest("/knowledge-bases/", { method: "GET" });
}

export function getKnowledgeBase(id) {
  return apiRequest(`/knowledge-bases/${encodeURIComponent(id)}/`, { method: "GET" });
}

export function createKnowledgeBase(data) {
  return apiRequest("/knowledge-bases/", { method: "POST", body: JSON.stringify(data) });
}

export function deleteKnowledgeBase(id) {
  return apiRequest(`/knowledge-bases/${encodeURIComponent(id)}/`, { method: "DELETE" });
}
