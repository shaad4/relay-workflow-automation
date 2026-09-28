"use client";

import { useState, useEffect } from "react";
import { getNodeDefinition } from "./nodeDefinitions";

// ─────────────────────────────────────────────────────────────────────────────
// Icons
// ─────────────────────────────────────────────────────────────────────────────
function TrashIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function SaveIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
      <polyline points="17 21 17 13 7 13 7 21" />
      <polyline points="7 3 7 8 15 8" />
    </svg>
  );
}

function SettingsIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function XIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Config field components
// ─────────────────────────────────────────────────────────────────────────────
function FieldLabel({ children }) {
  return (
    <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1 uppercase tracking-wide">
      {children}
    </label>
  );
}

function TextInput({ value, onChange, placeholder, mono = false }) {
  return (
    <input
      type="text"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full h-8 px-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-colors ${mono ? "font-mono" : ""}`}
    />
  );
}

function TextareaInput({ value, onChange, placeholder, rows = 3, mono = false }) {
  return (
    <textarea
      rows={rows}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full p-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-colors resize-none ${mono ? "font-mono" : ""}`}
    />
  );
}

function SelectInput({ value, onChange, options }) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="w-full h-8 px-2 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:outline-none"
    >
      {options.map(({ value: v, label }) => (
        <option key={v} value={v}>{label}</option>
      ))}
    </select>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Per-node-type configuration panels
// ─────────────────────────────────────────────────────────────────────────────
function WebhookConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>HTTP Method</FieldLabel>
        <SelectInput
          value={config.method}
          onChange={(v) => onChange("method", v)}
          options={[
            { value: "POST", label: "POST" },
            { value: "GET", label: "GET" },
          ]}
        />
      </div>
      <div>
        <FieldLabel>Endpoint Path</FieldLabel>
        <TextInput
          value={config.path}
          onChange={(v) => onChange("path", v)}
          placeholder="/hooks/my-webhook"
          mono
        />
        <p className="mt-1 text-[10px] text-[var(--text-tertiary)]">
          Relative path under your Relay base URL
        </p>
      </div>
    </div>
  );
}

function ScheduleConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Cron Expression</FieldLabel>
        <TextInput
          value={config.cron}
          onChange={(v) => onChange("cron", v)}
          placeholder="0 9 * * 1-5"
          mono
        />
        <p className="mt-1 text-[10px] text-[var(--text-tertiary)]">
          Standard 5-field cron (min hr dom mon dow)
        </p>
      </div>
      <div>
        <FieldLabel>Timezone</FieldLabel>
        <TextInput
          value={config.timezone}
          onChange={(v) => onChange("timezone", v)}
          placeholder="UTC"
        />
      </div>
    </div>
  );
}

function ManualConfig() {
  return (
    <div className="p-3 rounded-[6px] bg-[var(--elevated)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)] leading-relaxed">
      ▶ No configuration required. This node triggers the workflow manually via the dashboard or API.
    </div>
  );
}

function HttpRequestConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Method</FieldLabel>
        <SelectInput
          value={config.method}
          onChange={(v) => onChange("method", v)}
          options={[
            { value: "GET", label: "GET" },
            { value: "POST", label: "POST" },
            { value: "PUT", label: "PUT" },
            { value: "PATCH", label: "PATCH" },
            { value: "DELETE", label: "DELETE" },
          ]}
        />
      </div>
      <div>
        <FieldLabel>URL</FieldLabel>
        <TextInput
          value={config.url}
          onChange={(v) => onChange("url", v)}
          placeholder="https://api.example.com/endpoint"
          mono
        />
      </div>
      <div>
        <FieldLabel>Headers</FieldLabel>
        <TextareaInput
          value={config.headers}
          onChange={(v) => onChange("headers", v)}
          placeholder={"Content-Type: application/json\nAuthorization: Bearer {{token}}"}
          rows={2}
          mono
        />
        <p className="mt-1 text-[10px] text-[var(--text-tertiary)]">One header per line: Name: Value</p>
      </div>
      <div>
        <FieldLabel>Body</FieldLabel>
        <TextareaInput
          value={config.body}
          onChange={(v) => onChange("body", v)}
          placeholder='{"key": "value"}'
          rows={3}
          mono
        />
      </div>
    </div>
  );
}

function EmailConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>To Email</FieldLabel>
        <TextInput
          value={config.to}
          onChange={(v) => onChange("to", v)}
          placeholder="recipient@example.com"
        />
      </div>
      <div>
        <FieldLabel>Subject</FieldLabel>
        <TextInput
          value={config.subject}
          onChange={(v) => onChange("subject", v)}
          placeholder="Workflow Notification"
        />
      </div>
      <div>
        <FieldLabel>Message Body</FieldLabel>
        <TextareaInput
          value={config.body}
          onChange={(v) => onChange("body", v)}
          placeholder="Your automated message here."
          rows={3}
        />
      </div>
    </div>
  );
}

function RefundConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Charge / Order ID</FieldLabel>
        <TextInput
          value={config.charge_id}
          onChange={(v) => onChange("charge_id", v)}
          placeholder="ch_12345"
          mono
        />
      </div>
      <div>
        <FieldLabel>Reason</FieldLabel>
        <SelectInput
          value={config.reason}
          onChange={(v) => onChange("reason", v)}
          options={[
            { value: "requested_by_customer", label: "Requested by customer" },
            { value: "duplicate", label: "Duplicate charge" },
            { value: "fraudulent", label: "Fraudulent" },
          ]}
        />
      </div>
    </div>
  );
}

function AIConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Prompt / Instruction</FieldLabel>
        <TextareaInput
          value={config.prompt}
          onChange={(v) => onChange("prompt", v)}
          placeholder="Describe what the AI should do..."
          rows={4}
        />
      </div>
      <div>
        <FieldLabel>Model</FieldLabel>
        <SelectInput
          value={config.model}
          onChange={(v) => onChange("model", v)}
          options={[
            { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
            { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
            { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
          ]}
        />
      </div>
    </div>
  );
}

function RAGConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Knowledge Base ID</FieldLabel>
        <TextInput
          value={config.knowledge_base}
          onChange={(v) => onChange("knowledge_base", v)}
          placeholder="kb_customer_docs"
          mono
        />
      </div>
      <div>
        <FieldLabel>Query</FieldLabel>
        <TextInput
          value={config.query}
          onChange={(v) => onChange("query", v)}
          placeholder="{{input.message}}"
          mono
        />
      </div>
      <div>
        <FieldLabel>Top K Results</FieldLabel>
        <TextInput
          value={String(config.top_k ?? 5)}
          onChange={(v) => onChange("top_k", Number.parseInt(v, 10) || 5)}
          placeholder="5"
          mono
        />
      </div>
    </div>
  );
}

function ConditionConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Field / Variable</FieldLabel>
        <TextInput
          value={config.field}
          onChange={(v) => onChange("field", v)}
          placeholder="status_code"
          mono
        />
      </div>
      <div>
        <FieldLabel>Operator</FieldLabel>
        <SelectInput
          value={config.operator}
          onChange={(v) => onChange("operator", v)}
          options={[
            { value: "equals", label: "Equals (==)" },
            { value: "not_equals", label: "Not Equals (!=)" },
            { value: "contains", label: "Contains" },
            { value: "not_contains", label: "Does not contain" },
            { value: "greater_than", label: "Greater Than (>)" },
            { value: "less_than", label: "Less Than (<)" },
            { value: "is_empty", label: "Is empty" },
            { value: "is_not_empty", label: "Is not empty" },
          ]}
        />
      </div>
      <div>
        <FieldLabel>Value</FieldLabel>
        <TextInput
          value={config.value}
          onChange={(v) => onChange("value", v)}
          placeholder="200"
          mono
        />
      </div>
    </div>
  );
}

function ApprovalConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Approver Email</FieldLabel>
        <TextInput
          value={config.approver}
          onChange={(v) => onChange("approver", v)}
          placeholder="admin@company.com"
        />
      </div>
      <div>
        <FieldLabel>Timeout (hours)</FieldLabel>
        <TextInput
          value={String(config.timeout_hours ?? 24)}
          onChange={(v) => onChange("timeout_hours", Number.parseInt(v, 10) || 24)}
          placeholder="24"
          mono
        />
      </div>
      <div>
        <FieldLabel>Message</FieldLabel>
        <TextareaInput
          value={config.message}
          onChange={(v) => onChange("message", v)}
          placeholder="Please review and approve this request."
          rows={2}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NodeInspector
// ─────────────────────────────────────────────────────────────────────────────
export default function NodeInspector({
  selectedNode,
  onUpdateNode,
  onDeleteNode,
  onClose,
  isReadOnly = false,
}) {
  const [formData, setFormData] = useState({});
  const [nodeName, setNodeName] = useState("");
  const [hasLocalChanges, setHasLocalChanges] = useState(false);

  useEffect(() => {
    if (selectedNode) {
      setNodeName(selectedNode.data?.label ?? selectedNode.data?.name ?? "");
      setFormData({ ...(selectedNode.data?.config ?? {}) });
      setHasLocalChanges(false);
    } else {
      setNodeName("");
      setFormData({});
      setHasLocalChanges(false);
    }
  }, [selectedNode?.id]); // Reset only when node selection changes

  // Empty state
  if (!selectedNode) {
    return (
      <div className="w-80 bg-[var(--surface)] border-l border-[var(--border-subtle)] flex flex-col h-full select-none shrink-0 font-sans p-6 items-center justify-center text-center relative z-20 animate-in slide-in-from-right duration-150">
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            title="Close Inspector"
            className="absolute top-3 right-3 p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors cursor-pointer"
          >
            <XIcon className="w-4 h-4 stroke-[1.5]" />
          </button>
        )}
        <div className="w-10 h-10 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--text-tertiary)] mb-3">
          <SettingsIcon className="w-5 h-5 stroke-[1.5]" />
        </div>
        <h4 className="text-[14px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
          Node Inspector
        </h4>
        <p className="text-[12px] text-[var(--text-tertiary)] leading-relaxed max-w-[200px]">
          Click a node on the canvas to configure its settings.
        </p>
      </div>
    );
  }

  const typeId = selectedNode.data?.typeId ?? "custom";
  const def = getNodeDefinition(typeId);

  const handleFieldChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasLocalChanges(true);
  };

  const handleSave = (e) => {
    e?.preventDefault();
    if (isReadOnly) return;
    if (onUpdateNode) {
      onUpdateNode(selectedNode.id, {
        label: nodeName,
        name: nodeName,
        config: formData,
      });
      setHasLocalChanges(false);
    }
  };

  // Determine config panel
  const renderConfigPanel = () => {
    switch (typeId) {
      case "trigger.webhook":
        return <WebhookConfig config={formData} onChange={handleFieldChange} />;
      case "trigger.schedule":
        return <ScheduleConfig config={formData} onChange={handleFieldChange} />;
      case "trigger.manual":
        return <ManualConfig />;
      case "action.http_request":
        return <HttpRequestConfig config={formData} onChange={handleFieldChange} />;
      case "action.email":
        return <EmailConfig config={formData} onChange={handleFieldChange} />;
      case "action.refund":
        return <RefundConfig config={formData} onChange={handleFieldChange} />;
      case "ai.decision":
      case "ai.generate":
        return <AIConfig config={formData} onChange={handleFieldChange} />;
      case "ai.rag_search":
        return <RAGConfig config={formData} onChange={handleFieldChange} />;
      case "logic.condition":
        return <ConditionConfig config={formData} onChange={handleFieldChange} />;
      case "human.approval":
        return <ApprovalConfig config={formData} onChange={handleFieldChange} />;
      default:
        return (
          <div className="p-3 rounded-[6px] bg-[var(--elevated)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)]">
            No configuration fields for this node type.
          </div>
        );
    }
  };

  // Category accent color
  const getCategoryColor = () => {
    if (typeId.startsWith("trigger.")) return "bg-[#4F46E5]/10 text-[#4F46E5] border-[#4F46E5]/20";
    if (typeId.startsWith("action.")) return "bg-[#0EA5E9]/10 text-[#0EA5E9] border-[#0EA5E9]/20";
    if (typeId.startsWith("ai.")) return "bg-[#8B5CF6]/10 text-[#8B5CF6] border-[#8B5CF6]/20";
    if (typeId.startsWith("logic.") || typeId.startsWith("human.")) return "bg-[#D29922]/10 text-[#D29922] border-[#D29922]/20";
    return "bg-[var(--elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]";
  };

  return (
    <div className="w-80 bg-[var(--surface)] border-l border-[var(--border-subtle)] flex flex-col h-full select-none shrink-0 font-sans z-20 animate-in slide-in-from-right duration-150">
      {/* Header */}
      <div className="p-3 border-b border-[var(--border-subtle)] space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-[16px] shrink-0">{def.icon}</span>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-[var(--text-primary)] truncate">
                {nodeName || def.name}
              </div>
              <div className="text-[9px] font-mono text-[var(--text-tertiary)] truncate">
                {typeId}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-[4px] border shrink-0 ${getCategoryColor()}`}>
              {def.category}
            </span>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                title="Close Inspector"
                className="p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors cursor-pointer"
              >
                <XIcon className="w-4 h-4 stroke-[1.5]" />
              </button>
            )}
          </div>
        </div>

        {/* Node ID badge */}
        <div className="flex items-center gap-1">
          <span className="text-[9px] font-mono text-[var(--text-tertiary)] bg-[var(--elevated)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)]">
            id: {selectedNode.data?.nodeId ?? selectedNode.id}
          </span>
          {hasLocalChanges && !isReadOnly && (
            <span className="text-[9px] font-mono text-[#D29922] bg-[#D29922]/10 px-1.5 py-0.5 rounded border border-[#D29922]/20">
              unsaved
            </span>
          )}
        </div>
      </div>

      {/* Config form */}
      <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Node label */}
        <div>
          <FieldLabel>Node Label</FieldLabel>
          <input
            type="text"
            value={nodeName}
            onChange={(e) => {
              setNodeName(e.target.value);
              setHasLocalChanges(true);
            }}
            disabled={isReadOnly}
            className="w-full h-8 px-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>

        {/* Per-type config */}
        <div className="pt-2 border-t border-[var(--border-subtle)] space-y-3">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-tertiary)]">
            Configuration
          </div>
          {isReadOnly ? (
            <div className="opacity-60 pointer-events-none">
              {renderConfigPanel()}
            </div>
          ) : (
            renderConfigPanel()
          )}
        </div>

        {/* Action buttons */}
        {!isReadOnly && (
          <div className="pt-4 border-t border-[var(--border-subtle)] space-y-2">
            <button
              type="submit"
              className={`w-full h-8 px-3 rounded-[6px] font-medium text-[12px] transition-all duration-100 ease-out flex items-center justify-center gap-1.5 cursor-pointer shadow-none ${
                hasLocalChanges
                  ? "bg-[#4F46E5] hover:bg-[#6366F1] text-white"
                  : "bg-[var(--elevated)] hover:bg-[var(--border-subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]"
              }`}
            >
              <SaveIcon className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>{hasLocalChanges ? "Apply Changes" : "Saved"}</span>
            </button>

            <button
              type="button"
              onClick={() => onDeleteNode && onDeleteNode(selectedNode.id)}
              className="w-full h-8 px-3 rounded-[6px] border border-red-500/20 bg-red-500/5 hover:bg-red-500/15 text-red-600 dark:text-red-400 font-medium text-[12px] transition-all duration-100 ease-out flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <TrashIcon className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>Delete Node</span>
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
