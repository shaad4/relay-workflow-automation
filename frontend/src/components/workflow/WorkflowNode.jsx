"use client";

import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { getNodeDefinition } from "./nodeDefinitions";

function WorkflowNode({ data, selected }) {
  const typeId = data?.typeId || data?.node_type || "custom";
  const def = getNodeDefinition(typeId);
  const name = data?.name || data?.label || def.name;
  const config = data?.config || data?.data || {};

  // Formatter for config preview line
  const getConfigSummary = () => {
    if (typeId === "trigger.webhook") return `POST ${config.path || "/hooks/..."}`;
    if (typeId === "trigger.schedule") return `Cron: ${config.cron || "0 0 * * *"}`;
    if (typeId === "trigger.manual") return "Manual trigger";
    if (typeId === "action.http_request") return `${config.method || "POST"} ${config.url || "https://..."}`;
    if (typeId === "action.email") return `To: ${config.to || "user@..."}`;
    if (typeId === "action.refund") return `Charge: ${config.charge_id || "ch_..."}`;
    if (typeId === "ai.decision") return `Model: ${config.model || "gemini-2.5-flash"}`;
    if (typeId === "ai.rag_search") return `KB: ${config.knowledge_base || "default"}`;
    if (typeId === "ai.generate") return `Model: ${config.model || "gemini-2.5-flash"}`;
    if (typeId === "logic.condition") return `${config.field || "field"} ${config.operator || "=="} ${config.value || "val"}`;
    if (typeId === "human.approval") return `Approver: ${config.approver || "admin@..."}`;
    return "Configured";
  };

  const isTrigger = typeId.startsWith("trigger.");
  const isCondition = typeId === "logic.condition";

  return (
    <div
      className={`w-52 bg-[var(--surface)] border rounded-md p-2 text-[var(--text-primary)] transition-all duration-100 ease-out select-none font-sans ${
        selected
          ? "border-[#4F46E5] ring-2 ring-[#4F46E5]/25 shadow-sm"
          : "border-[var(--border-subtle)] hover:border-[var(--border-strong)] shadow-2xs"
      }`}
    >
      {/* Top Handle (Input) - Triggers don't need top handles */}
      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-2 !h-2 !bg-[var(--surface)] !border-2 !border-[var(--text-tertiary)] hover:!border-[#4F46E5] transition-colors !-top-1"
        />
      )}

      {/* Node Header */}
      <div className="flex items-center justify-between gap-1.5 mb-1 pb-1 border-b border-[var(--border-subtle)]/60">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[12px] shrink-0">{def.icon}</span>
          <span className="text-[12px] font-semibold text-[var(--text-primary)] truncate leading-tight">
            {name}
          </span>
        </div>

        <span className="text-[8px] font-mono tracking-wider text-[var(--text-tertiary)] uppercase bg-[var(--canvas)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)] shrink-0">
          {def.category}
        </span>
      </div>

      {/* Node Type ID & Config Summary */}
      <div className="space-y-0.5">
        <div className="text-[9px] font-mono text-[var(--text-tertiary)] truncate">
          {typeId}
        </div>
        <div className="text-[10px] font-mono text-[var(--text-secondary)] truncate bg-[var(--canvas)]/80 px-1.5 py-0.5 rounded border border-[var(--border-subtle)]/50">
          {getConfigSummary()}
        </div>
      </div>

      {/* Status indicator */}
      <div className="mt-1 flex items-center justify-between text-[9px] text-[var(--text-tertiary)] pt-0.5">
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[#3FB950]" />
          <span className="text-[9px]">Ready</span>
        </div>
        {data?.node_id && (
          <span className="font-mono text-[8px] text-[var(--text-tertiary)]">
            #{data.node_id}
          </span>
        )}
      </div>

      {/* Bottom Handle (Output) */}
      {!isCondition ? (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!w-2 !h-2 !bg-[var(--surface)] !border-2 !border-[var(--text-tertiary)] hover:!border-[#4F46E5] transition-colors !-bottom-1"
        />
      ) : (
        /* Condition node has true/false outputs */
        <>
          <Handle
            type="source"
            position={Position.Bottom}
            id="true"
            className="!w-2 !h-2 !bg-[#3FB950] !border-2 !border-[var(--surface)] !-ml-6 !-bottom-1"
            title="True"
          />
          <Handle
            type="source"
            position={Position.Bottom}
            id="false"
            className="!w-2 !h-2 !bg-[#F85149] !border-2 !border-[var(--surface)] !ml-6 !-bottom-1"
            title="False"
          />
        </>
      )}
    </div>
  );
}

export default memo(WorkflowNode);
