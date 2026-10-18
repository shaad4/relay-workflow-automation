"use client";

import { InspectorInput, InspectorSelect } from "./InspectorControls";
import { branchOptions } from "./branchOptions";

export default function BranchConditionField({ edge, source, nodes, edges, isReadOnly, onChange }) {
  const options = branchOptions(source, nodes, edges);
  const value = edge.data?.condition ?? "";
  const isBranch = ["human.approval", "logic.condition"].includes(source?.data?.typeId);
  const stale = options !== null && value && !options.some((option) => option.value === value);
  const used = new Set(edges.filter((item) => item.source === edge.source && item.id !== edge.id).map((item) => item.data?.condition));
  const className = "w-full h-8 px-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--accent)] focus:outline-none disabled:opacity-60";
  return (
    <div>
      <label className="block">
        <span className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">{isBranch ? "Run this branch when" : "Condition label"}</span>
        {options !== null ? (
          <InspectorSelect aria-label="Branch outcome" aria-invalid={!!stale} value={value} readOnly={isReadOnly} onChange={(event) => onChange(event.target.value)} className={className}>
            <option value="">Choose an outcome…</option>
            {stale && <option value={value} disabled>{value} — unavailable</option>}
            {options.map((option) => <option key={option.value} value={option.value} disabled={used.has(option.value) && option.value !== value}>{option.label}{used.has(option.value) && option.value !== value ? " — already connected" : ""}</option>)}
          </InspectorSelect>
        ) : (
          <InspectorInput value={value} readOnly={isReadOnly} onChange={(event) => onChange(event.target.value)} placeholder={isBranch ? "Exact outcome value" : "Optional label"} maxLength={255} className={className} />
        )}
      </label>
      {stale && <p role="alert" className="mt-1 text-[10px] text-red-500">This outcome is no longer available. Choose a current outcome.</p>}
      {options?.length === 0 && <p className="mt-1 text-[10px] text-[var(--text-tertiary)]">Configure the Condition value and its source outcomes first.</p>}
      {source?.data?.typeId === "logic.condition" && <p className="mt-1 text-[10px] leading-4 text-[var(--text-tertiary)]">{options === null ? "This value has no predefined outcomes. Enter its exact expected value, or choose an AI Decision output in the Condition node to select from its outcomes." : "Outcomes come from this Condition’s value and source configuration."}</p>}
    </div>
  );
}
