"use client";

import { useMemo, useState } from "react";

const outputsByType = {
  "action.http_request": ["status_code", "body", "headers", "success"],
  "action.email": ["message_id", "thread_id", "label_ids", "success"],
};

function previousNodesFor(nodes, edges, currentNodeId) {
  const byId = new Map((nodes || []).map((node) => [String(node.id), node]));
  const previousIds = new Set();
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
    .filter((node) => node && !node.data?.typeId?.startsWith("trigger."))
    .reverse();
}

export default function VariablePicker({ nodes, edges, currentNode, onInsert }) {
  const [open, setOpen] = useState(false);
  const [triggerPath, setTriggerPath] = useState("");
  const [expandedNode, setExpandedNode] = useState(null);
  const previousNodes = useMemo(
    () => previousNodesFor(nodes, edges, currentNode?.id),
    [nodes, edges, currentNode?.id]
  );

  const insert = (expression) => {
    onInsert(expression);
    setOpen(false);
  };

  const insertTriggerPath = () => {
    const path = triggerPath.trim().replace(/^\.+|\.+$/g, "");
    if (!path || !/^[\w$-]+(?:\.[\w$-]+)*$/.test(path)) return;
    insert(`{{trigger.data.${path}}}`);
    setTriggerPath("");
  };

  return (
    <div className="relative inline-flex">
      <button type="button" aria-label="Insert variable" title="Insert variable" aria-expanded={open} onClick={() => setOpen((value) => !value)} className="grid h-6 w-6 place-items-center rounded-[5px] border border-[var(--border-subtle)] font-mono text-[10px] font-semibold text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)]/50 hover:bg-[var(--accent)]/5 hover:text-[var(--accent)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/40">{`{}`}</button>
      {open && <div className="absolute right-0 top-7 z-[90] w-72 max-h-[min(360px,65vh)] overflow-y-auto rounded-[8px] border border-[var(--border-default)] bg-[var(--surface)] p-2 shadow-2xl" role="dialog" aria-label="Variable picker">
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-1 pb-2"><div><p className="text-[11px] font-semibold text-[var(--text-primary)]">Insert variable</p><p className="mt-0.5 text-[9px] text-[var(--text-tertiary)]">Adds an expression at the end of this value.</p></div><button type="button" onClick={() => setOpen(false)} aria-label="Close variable picker" className="rounded px-1.5 text-[15px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)]">×</button></div>
        <section className="py-2"><p className="px-1 text-[9px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Trigger <span className="normal-case tracking-normal">› Data</span></p><div className="mt-1.5 flex gap-1.5"><input aria-label="Trigger data path" value={triggerPath} onChange={(event) => setTriggerPath(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); insertTriggerPath(); } }} placeholder="email or body.email" className="h-8 min-w-0 flex-1 rounded-[5px] border border-[var(--border-default)] bg-[var(--input-bg)] px-2 text-[10px] font-mono text-[var(--text-primary)] outline-none focus:border-[var(--accent)]"/><button type="button" onClick={insertTriggerPath} disabled={!triggerPath.trim()} className="h-8 rounded-[5px] bg-[var(--accent)] px-2 text-[10px] font-medium text-white disabled:opacity-40">Insert</button></div><p className="mt-1 px-1 text-[9px] leading-4 text-[var(--text-tertiary)]">Enter a field path from the incoming trigger data. Use dots for nested fields.</p></section>
        <section className="border-t border-[var(--border-subtle)] py-2"><p className="px-1 text-[9px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Previous nodes</p>{previousNodes.length === 0 ? <p className="px-1 py-2 text-[10px] text-[var(--text-tertiary)]">No previous action nodes in this workflow path.</p> : <div className="mt-1 space-y-0.5">{previousNodes.map((node) => { const typeId = node.data?.typeId; const fields = outputsByType[typeId] || []; const nodeId = node.data?.nodeId || node.id; const label = node.data?.label || node.data?.name || typeId; return <div key={node.id}><button type="button" onClick={() => setExpandedNode(expandedNode === node.id ? null : node.id)} className="flex w-full items-center gap-2 rounded-[5px] px-1.5 py-1.5 text-left hover:bg-[var(--elevated)]"><span className="text-[10px] text-[var(--text-tertiary)]">{expandedNode === node.id ? "▾" : "▸"}</span><span className="min-w-0 flex-1 truncate text-[10px] font-medium text-[var(--text-primary)]">{label}</span><code className="max-w-24 truncate font-mono text-[9px] text-[var(--text-tertiary)]">{nodeId}</code></button>{expandedNode === node.id && <div className="ml-4 border-l border-[var(--border-subtle)] pl-2">{fields.length ? fields.map((field) => <button key={field} type="button" onClick={() => insert(`{{nodes.${nodeId}.${field}}}`)} className="block w-full rounded px-2 py-1 text-left font-mono text-[10px] text-[var(--text-secondary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]">{field}</button>) : <p className="px-2 py-1 text-[9px] text-[var(--text-tertiary)]">No output fields defined for this node yet.</p>}</div>}</div>; })}</div>}</section>
      </div>}
    </div>
  );
}
