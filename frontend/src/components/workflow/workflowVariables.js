export const outputsByType = {
  "ai.generate": ["content", "model", "input_tokens", "output_tokens"],
  "ai.decision": [
    "decision",
    "reason",
    "data",
    "model",
    "input_tokens",
    "output_tokens",
  ],
  "ai.rag_search": ["chunks", "context"],
  "action.http_request": ["status_code", "body", "headers", "success"],
  "action.email": ["message_id", "thread_id", "label_ids", "success"],
  "action.refund": ["refund_id", "payment_id", "amount", "status", "success"],
};

export function previousNodesFor(
  nodes,
  edges,
  currentNodeId,
  includeTriggers = false,
) {
  const byId = new Map((nodes || []).map((node) => [String(node.id), node]));
  const previousIds = new Set();
  const followingIds = new Set();
  const following = [String(currentNodeId)];
  while (following.length) {
    const source = following.pop();
    for (const edge of edges || []) {
      const target = String(edge.target);
      if (String(edge.source) === source && !followingIds.has(target)) {
        followingIds.add(target);
        following.push(target);
      }
    }
  }
  const pending = (edges || [])
    .filter((edge) => String(edge.target) === String(currentNodeId))
    .map((edge) => String(edge.source));

  while (pending.length) {
    const id = pending.pop();
    if (previousIds.has(id) || id === String(currentNodeId)) continue;
    previousIds.add(id);
    for (const edge of edges || []) {
      if (String(edge.target) === id) pending.push(String(edge.source));
    }
  }

  return [...previousIds]
    .map((id) => byId.get(id))
    .filter(
      (node) =>
        node &&
        !followingIds.has(String(node.id)) &&
        (includeTriggers || !node.data?.typeId?.startsWith("trigger.")),
    )
    .reverse();
}
