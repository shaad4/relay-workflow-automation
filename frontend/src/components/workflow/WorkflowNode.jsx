"use client";

import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { getNodeDefinition } from "./nodeDefinitions";

const categoryColors = {
  triggers: "#f59e0b",
  actions: "#38bdf8",
  ai: "#a78bfa",
  logic: "#34d399",
  human: "#fb7185",
};

function WorkflowNode({ data, selected }) {
  const typeId = data?.typeId || data?.node_type || "custom";
  const def = getNodeDefinition(typeId);
  const name = data?.name || data?.label || def.name;
  const config = data?.config || data?.data || {};
  const group = typeId.split(".")[0];
  const color = categoryColors[group] || "#818cf8";
  const isTrigger = group === "trigger";
  const isCondition = typeId === "logic.condition";

  const getConfigSummary = () => {
    if (typeId === "trigger.webhook") return `${config.method || "POST"}  ${config.path || "/hooks/..."}`;
    if (typeId === "trigger.schedule") return `${config.cron || "0 0 * * *"}  ·  ${config.timezone || "UTC"}`;
    if (typeId === "trigger.manual") return "Manual trigger";
    if (typeId === "action.http_request") return `${config.method || "POST"}  ${config.url || "https://..."}`;
    if (typeId === "action.email") return `To  ${config.to || "user@..."}`;
    if (typeId === "action.refund") return `Charge  ${config.charge_id || "ch_..."}`;
    if (typeId === "ai.decision" || typeId === "ai.generate") return config.model || "gemini-2.5-flash";
    if (typeId === "ai.rag_search") return `Index  ${config.knowledge_base || "default"}`;
    if (typeId === "logic.condition") return `${config.field || "field"}  ${config.operator || "=="}  ${config.value || "value"}`;
    if (typeId === "human.approval") return `Approver  ${config.approver || "admin@..."}`;
    return "Configured";
  };

  const handleClass = "workflow-handle !h-3 !w-3 !rounded-full !border-2 !border-[var(--canvas)] !bg-[#737373] transition-all hover:!bg-white hover:!scale-125";

  return (
    <div
      className={`workflow-node group relative w-[248px] overflow-visible rounded-xl border text-[var(--text-primary)] font-sans transition-all duration-150 ${selected ? "is-selected" : ""}`}
      style={{ "--node-accent": color }}
    >
      {!isTrigger && <Handle type="target" position={Position.Top} className={`${handleClass} !-top-1.5`} />}

      <div className="h-[3px] rounded-t-xl" style={{ background: `linear-gradient(90deg, ${color}, ${color}55)` }} />
      <div className="flex items-center gap-3 px-3.5 pt-3 pb-2.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border text-[17px]" style={{ color, borderColor: `${color}35`, background: `${color}12` }}>
          {def.icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="workflow-node-title truncate text-[13px] font-semibold tracking-[-0.02em]">{name}</div>
          <div className="mt-0.5 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="workflow-node-category text-[10px] font-medium capitalize">{def.category || group}</span>
          </div>
        </div>
        <span className="text-[var(--text-tertiary)] opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true">···</span>
      </div>

      <div className="workflow-node-divider mx-3.5 border-t" />
      <div className="px-3.5 py-2.5">
        <div className="workflow-node-config truncate rounded-md border px-2.5 py-2 font-mono text-[10px] leading-4" title={getConfigSummary()}>
          {getConfigSummary()}
        </div>
      </div>

      <div className="workflow-node-footer flex items-center justify-between border-t px-3.5 py-2 text-[10px] text-[var(--text-tertiary)]">
        <span className="inline-flex items-center gap-1.5"><span className="h-1.5 w-1.5 rounded-full bg-[#35c98a] shadow-[0_0_8px_#35c98a80]" />Ready</span>
        <span className="workflow-node-id font-mono">{data?.nodeId || data?.node_id || "step"}</span>
      </div>

      {!isCondition ? (
        <Handle type="source" position={Position.Bottom} className={`${handleClass} !-bottom-1.5`} />
      ) : (
        <>
          <Handle type="source" position={Position.Bottom} id="true" className={`${handleClass} !-bottom-1.5 !bg-[#35c98a] !-ml-7`} title="True" />
          <Handle type="source" position={Position.Bottom} id="false" className={`${handleClass} !-bottom-1.5 !bg-[#fb7185] !ml-7`} title="False" />
        </>
      )}
    </div>
  );
}

export default memo(WorkflowNode);
