import { previousNodesFor } from "./workflowVariables.js";

// null means the source has no declared set of outcomes.
export function branchOptions(source, nodes = [], edges = []) {
  if (source?.data?.typeId === "human.approval") {
    return [{ value: "approved", label: "Approved" }, { value: "rejected", label: "Rejected" }];
  }
  if (source?.data?.typeId !== "logic.condition") return null;
  const config = source.data.config ?? {};
  if (Object.keys(config).some((key) => key !== "value")) return null;
  const value = typeof config.value === "string" ? config.value.trim() : "";
  if (!value) return [];
  if (!value.includes("{{") && !value.includes("}}")) return [{ value, label: value }];
  const reference = value.match(/^\{\{\s*nodes\.([^\s.{}]+)\.([^\s.{}]+)\s*\}\}$/);
  if (!reference) return null;
  const upstream = previousNodesFor(nodes, edges, source.id, true)
    .find((node) => (node.data?.nodeId ?? node.id) === reference[1]);
  if (upstream?.data?.typeId === "ai.decision" && reference[2] === "decision") {
    const decisions = upstream.data.config?.allowed_decisions;
    return [...new Set((Array.isArray(decisions) ? decisions : [])
      .filter((item) => typeof item === "string" && item.trim())
      .map((item) => item.trim().toUpperCase()))]
      .map((item) => ({ value: item, label: item }));
  }
  if (["action.http_request", "action.email", "action.refund"].includes(upstream?.data?.typeId) && reference[2] === "success") {
    return [{ value: "true", label: "True" }, { value: "false", label: "False" }];
  }
  return null;
}
