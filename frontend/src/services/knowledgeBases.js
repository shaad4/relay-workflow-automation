import { apiRequest } from "@/lib/api";

export function listKnowledgeBases() {
  return apiRequest("/knowledge-bases/", { method: "GET" });
}

export function getKnowledgeBase(id) {
  return apiRequest(`/knowledge-bases/${encodeURIComponent(id)}/`, {
    method: "GET",
  });
}

export function createKnowledgeBase(data) {
  return apiRequest("/knowledge-bases/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function deleteKnowledgeBase(id) {
  return apiRequest(`/knowledge-bases/${encodeURIComponent(id)}/`, {
    method: "DELETE",
  });
}

export function uploadDocument(id, file, options = {}) {
  const body = new FormData();
  body.append("file", file);
  return apiRequest(`/knowledge-bases/${encodeURIComponent(id)}/documents/`, {
    ...options,
    method: "POST",
    body,
  });
}

export function listDocuments(id, options = {}) {
  return apiRequest(`/knowledge-bases/${encodeURIComponent(id)}/documents/`, {
    ...options,
    method: "GET",
  });
}

export function deleteDocument(id, documentId) {
  return apiRequest(
    `/knowledge-bases/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}/`,
    { method: "DELETE" },
  );
}

export function retryDocument(id, documentId) {
  return apiRequest(
    `/knowledge-bases/${encodeURIComponent(id)}/documents/${encodeURIComponent(documentId)}/retry/`,
    { method: "POST" },
  );
}
