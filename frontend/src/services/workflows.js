import { apiRequest } from "@/lib/api";

function getHeaders(token) {
  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {};
}

export async function getWorkflows(token) {
  return apiRequest("/workflows/", {
    method: "GET",
    headers: getHeaders(token),
  });
}

export async function createWorkflow(token, workflowData) {
  return apiRequest("/workflows/", {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify(workflowData),
  });
}

export async function getWorkflow(token, workflowId) {
  return apiRequest(`/workflows/${workflowId}/`, {
    method: "GET",
    headers: getHeaders(token),
  });
}

export async function updateWorkflow(token, workflowId, workflowData) {
  return apiRequest(`/workflows/${workflowId}/`, {
    method: "PATCH",
    headers: getHeaders(token),
    body: JSON.stringify(workflowData),
  });
}

export async function activateWorkflow(token, workflowId) {
  return apiRequest(`/workflows/${workflowId}/activate/`, {
    method: "POST",
    headers: getHeaders(token),
  });
}

export async function deactivateWorkflow(token, workflowId) {
  return apiRequest(`/workflows/${workflowId}/deactivate/`, {
    method: "POST",
    headers: getHeaders(token),
  });
}

export async function deleteWorkflow(token, workflowId) {
  return apiRequest(`/workflows/${workflowId}/`, {
    method: "DELETE",
    headers: getHeaders(token),
  });
}

export async function getWorkflowVersions(token, workflowId) {
  return apiRequest(`/workflows/${workflowId}/versions/`, {
    method: "GET",
    headers: getHeaders(token),
  });
}

export async function getWorkflowVersion(token, workflowId, versionNumber) {
  return apiRequest(`/workflows/${workflowId}/versions/${versionNumber}`, {
    method: "GET",
    headers: getHeaders(token),
  });
}

export async function createDraftVersion(token, workflowId) {
  return apiRequest(`/workflows/${workflowId}/draft/`, {
    method: "POST",
    headers: getHeaders(token),
  });
}

export async function getWorkflowNodes(token, workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/`,
    {
      method: "GET",
      headers: getHeaders(token),
    }
  );
}

export async function createWorkflowNode(token, workflowId, versionNumber, nodeData) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/`,
    {
      method: "POST",
      headers: getHeaders(token),
      body: JSON.stringify(nodeData),
    }
  );
}

export async function updateWorkflowNode(
  token,
  workflowId,
  versionNumber,
  nodeId,
  nodeData
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/${nodeId}/`,
    {
      method: "PATCH",
      headers: getHeaders(token),
      body: JSON.stringify(nodeData),
    }
  );
}

export async function deleteWorkflowNode(
  token,
  workflowId,
  versionNumber,
  nodeId
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/${nodeId}/`,
    {
      method: "DELETE",
      headers: getHeaders(token),
    }
  );
}

export async function getWorkflowEdges(token, workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/`,
    {
      method: "GET",
      headers: getHeaders(token),
    }
  );
}

export async function createWorkflowEdge(token, workflowId, versionNumber, edgeData) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/`,
    {
      method: "POST",
      headers: getHeaders(token),
      body: JSON.stringify(edgeData),
    }
  );
}

export async function updateWorkflowEdge(
  token,
  workflowId,
  versionNumber,
  edgeId,
  edgeData
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/${edgeId}/`,
    {
      method: "PATCH",
      headers: getHeaders(token),
      body: JSON.stringify(edgeData),
    }
  );
}

export async function deleteWorkflowEdge(
  token,
  workflowId,
  versionNumber,
  edgeId
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/${edgeId}/`,
    {
      method: "DELETE",
      headers: getHeaders(token),
    }
  );
}

export async function validateWorkflow(token, workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/validate/`,
    {
      method: "POST",
      headers: getHeaders(token),
    }
  );
}

export async function publishWorkflow(token, workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/publish/`,
    {
      method: "POST",
      headers: getHeaders(token),
    }
  );
}
