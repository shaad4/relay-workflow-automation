import {
  normalizeRAGConfiguration,
  normalizeDecisionConfiguration,
} from "./configValidation.js";

// Compare only persisted fields. React Flow selection and temporary UUIDs are UI state.
export function workflowSaveSnapshot(nodes, edges) {
  const logicalIds = new Map(nodes.map((node) => [node.id, node.data.nodeId]));
  return JSON.stringify({
    nodes: nodes
      .map((node) => ({
        nodeId: node.data.nodeId,
        type: node.data.typeId,
        label: node.data.label,
        x: Math.round(node.position.x),
        y: Math.round(node.position.y),
        config:
          node.data.typeId === "ai.rag_search"
            ? normalizeRAGConfiguration(node.data.config)
            : node.data.typeId === "ai.decision"
              ? normalizeDecisionConfiguration(node.data.config)
              : (node.data.config ?? {}),
      }))
      .sort((a, b) => a.nodeId.localeCompare(b.nodeId)),
    edges: edges
      .map((edge) => ({
        source: logicalIds.get(edge.source) ?? edge.source,
        target: logicalIds.get(edge.target) ?? edge.target,
        condition: edge.data?.condition ?? null,
      }))
      .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
  });
}

export function workflowChangedDuringSave(
  saved,
  current,
  savedRevision,
  currentRevision,
) {
  return (
    savedRevision !== currentRevision ||
    saved !== workflowSaveSnapshot(current.nodes, current.edges)
  );
}
