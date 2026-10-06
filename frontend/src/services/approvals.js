import { apiRequest } from "@/lib/api";

export function getApprovals() {
  return apiRequest("/approvals/", { method: "GET" });
}

export function getApproval(approvalId) {
  return apiRequest(`/approvals/${encodeURIComponent(approvalId)}/`, { method: "GET" });
}

export function approveApproval(approvalId) {
  return apiRequest(`/approvals/${encodeURIComponent(approvalId)}/approve/`, { method: "POST" });
}

export function rejectApproval(approvalId) {
  return apiRequest(`/approvals/${encodeURIComponent(approvalId)}/reject/`, { method: "POST" });
}
