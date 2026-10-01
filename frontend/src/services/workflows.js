import { apiRequest } from "@/lib/api";

export async function getWorkflows() {
  return apiRequest("/workflows/", {
    method: "GET",
  });
}

export async function createWorkflow(workflowData) {
  return apiRequest("/workflows/", {
    method: "POST",
    body: JSON.stringify(workflowData),
  });
}

export async function getWorkflow(workflowId) {
  return apiRequest(`/workflows/${workflowId}/`, {
    method: "GET",
  });
}

export async function updateWorkflow(workflowId, workflowData) {
  return apiRequest(`/workflows/${workflowId}/`, {
    method: "PATCH",
    body: JSON.stringify(workflowData),
  });
}

export async function activateWorkflow(workflowId) {
  return apiRequest(`/workflows/${workflowId}/activate/`, {
    method: "POST",
  });
}

export async function deactivateWorkflow(workflowId) {
  return apiRequest(`/workflows/${workflowId}/deactivate/`, {
    method: "POST",
  });
}

export async function deleteWorkflow(workflowId) {
  return apiRequest(`/workflows/${workflowId}/`, {
    method: "DELETE",
  });
}

export async function getWorkflowVersions(workflowId) {
  return apiRequest(`/workflows/${workflowId}/versions/`, {
    method: "GET",
  });
}

export async function getWorkflowVersion(workflowId, versionNumber) {
  return apiRequest(`/workflows/${workflowId}/versions/${versionNumber}`, {
    method: "GET",
  });
}

export async function deleteWorkflowVersion(workflowId, versionNumber) {
  return apiRequest(`/workflows/${workflowId}/versions/${versionNumber}/`, {
    method: "DELETE",
  });
}

export async function createDraftVersion(workflowId) {
  return apiRequest(`/workflows/${workflowId}/draft/`, {
    method: "POST",
  });
}

export async function getWorkflowNodes(workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/`,
    {
      method: "GET",
    }
  );
}

export async function createWorkflowNode(workflowId, versionNumber, nodeData) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/`,
    {
      method: "POST",
      body: JSON.stringify(nodeData),
    }
  );
}

export async function updateWorkflowNode(
  workflowId,
  versionNumber,
  nodeId,
  nodeData
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/${nodeId}/`,
    {
      method: "PATCH",
      body: JSON.stringify(nodeData),
    }
  );
}

export async function deleteWorkflowNode(
  workflowId,
  versionNumber,
  nodeId
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/nodes/${nodeId}/`,
    {
      method: "DELETE",
    }
  );
}

export async function getWorkflowEdges(workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/`,
    {
      method: "GET",
    }
  );
}

export async function createWorkflowEdge(workflowId, versionNumber, edgeData) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/`,
    {
      method: "POST",
      body: JSON.stringify(edgeData),
    }
  );
}

export async function updateWorkflowEdge(
  workflowId,
  versionNumber,
  edgeId,
  edgeData
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/${edgeId}/`,
    {
      method: "PATCH",
      body: JSON.stringify(edgeData),
    }
  );
}

export async function deleteWorkflowEdge(
  workflowId,
  versionNumber,
  edgeId
) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/edges/${edgeId}/`,
    {
      method: "DELETE",
    }
  );
}

export async function validateWorkflow(workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/validate/`,
    {
      method: "POST",
    }
  );
}

export async function publishWorkflow(workflowId, versionNumber) {
  return apiRequest(
    `/workflows/${workflowId}/versions/${versionNumber}/publish/`,
    {
      method: "POST",
    }
  );
}
