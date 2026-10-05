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

function ExpressionOption({ expression, label, onClick }) {
  return (
    <button type="button" onClick={onClick} title={`Insert ${expression}`} className="group block w-full rounded-[5px] px-2 py-1.5 text-left transition-colors hover:bg-[var(--elevated)] focus:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)]">
      <span className="block text-[10px] font-medium text-[var(--text-primary)]">{label}</span>
      <code className="mt-1 block break-all rounded-[4px] border border-sky-500/25 bg-sky-500/10 px-1.5 py-1 font-mono text-[9px] leading-4 text-sky-400">{expression}</code>
    </button>
  );
}

export default function VariablePicker({ nodes, edges, currentNode, onInsert }) {
  const [open, setOpen] = useState(false);
  const [triggerPath, setTriggerPath] = useState("");
  const [expandedNode, setExpandedNode] = useState(null);
  const [search, setSearch] = useState("");
  const previousNodes = useMemo(
    () => previousNodesFor(nodes, edges, currentNode?.id),
    [nodes, edges, currentNode?.id]
  );
  const matchingNodes = previousNodes.filter((node) => {
    const query = search.trim().toLowerCase();
    return !query || `${node.data?.label || node.data?.name || ""} ${node.data?.nodeId || ""} ${(outputsByType[node.data?.typeId] || []).join(" ")}`.toLowerCase().includes(query);
  });

  const insert = (expression) => {
    onInsert(expression);
    setOpen(false);
    setSearch("");
  };

  const insertTriggerPath = () => {
    const path = triggerPath.trim().replace(/^\.+|\.+$/g, "");
    if (!path || !/^[\w$-]+(?:\.[\w$-]+)*$/.test(path)) return;
    insert(`{{trigger.data.${path}}}`);
    setTriggerPath("");
  };

  return (
    <div className="relative inline-flex">
      <button type="button" aria-label="Insert variable" title="Insert variable" aria-expanded={open} onClick={() => setOpen((value) => !value)} className={`inline-flex h-6 items-center gap-1 rounded-[5px] border px-1.5 font-mono text-[9px] font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40 ${open ? "border-sky-500/40 bg-sky-500/10 text-sky-400" : "border-sky-500/20 text-sky-400 hover:border-sky-500/40 hover:bg-sky-500/5"}`}><span aria-hidden="true">{`{{ }}`}</span><span className="font-sans font-medium">Variable</span></button>
      {open && <div className="absolute bottom-[calc(100%+6px)] right-0 z-[100] w-[min(280px,calc(100vw-24px))] overflow-hidden rounded-[8px] border border-[var(--border-strong)] bg-[var(--surface)] shadow-2xl" role="dialog" aria-label="Variable picker">
        <div className="border-b border-[var(--border-subtle)] p-2.5">
          <div className="flex items-center justify-between gap-2"><div><p className="text-[11px] font-semibold text-[var(--text-primary)]">Variables</p><p className="mt-0.5 text-[9px] text-[var(--text-tertiary)]">Select a token to insert it into this value.</p></div><button type="button" onClick={() => setOpen(false)} aria-label="Close variable picker" className="grid h-6 w-6 place-items-center rounded text-[14px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)]">×</button></div>
          <div className="mt-2 flex h-8 items-center gap-2 rounded-[5px] border border-[var(--border-default)] bg-[var(--input-bg)] px-2"><span className="text-[var(--text-tertiary)]" aria-hidden="true">⌕</span><input aria-label="Search previous node variables" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search previous node outputs" className="min-w-0 flex-1 bg-transparent text-[10px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-disabled)]" /></div>
        </div>
        <div className="max-h-[min(340px,55vh)] overflow-y-auto p-2">
          <section className="pb-2">
            <p className="px-1.5 pb-1 text-[9px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Trigger <span className="font-normal normal-case tracking-normal">/ Data</span></p>
            <div className="flex gap-1.5 px-1"><input aria-label="Trigger data path" value={triggerPath} onChange={(event) => setTriggerPath(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); insertTriggerPath(); } }} placeholder="field.path" className="h-8 min-w-0 flex-1 rounded-[5px] border border-[var(--border-default)] bg-[var(--input-bg)] px-2 font-mono text-[10px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-disabled)] focus:border-[var(--accent)]"/><button type="button" onClick={insertTriggerPath} disabled={!triggerPath.trim()} className="h-8 rounded-[5px] bg-[var(--accent)] px-2.5 text-[10px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40">Insert</button></div>
            {triggerPath.trim() && <div className="mx-1 mt-1.5 rounded-[5px] bg-sky-500/10 px-2 py-1.5"><span className="mr-1 text-[8px] uppercase tracking-wide text-[var(--text-tertiary)]">Token</span><code className="break-all font-mono text-[9px] text-sky-400">{`{{trigger.data.${triggerPath.trim().replace(/^\.+|\.+$/g, "")}}}`}</code></div>}
            <p className="px-1.5 pt-1 text-[9px] leading-4 text-[var(--text-tertiary)]">Use a field from the incoming payload; dots select nested fields.</p>
          </section>
          <section className="border-t border-[var(--border-subtle)] pt-2">
            <p className="px-1.5 pb-1 text-[9px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Previous nodes</p>
            {matchingNodes.length === 0 ? <p className="px-1.5 py-2 text-[10px] text-[var(--text-tertiary)]">{previousNodes.length ? "No outputs match your search." : "Connect an action before this node to use its outputs."}</p> : <div className="space-y-0.5">{matchingNodes.map((node) => {
              const typeId = node.data?.typeId;
              const fields = outputsByType[typeId] || [];
              const nodeId = node.data?.nodeId || node.id;
              const label = node.data?.label || node.data?.name || typeId;
              const expanded = expandedNode === node.id;
              return <div key={node.id}>
                <button type="button" aria-expanded={expanded} onClick={() => setExpandedNode(expanded ? null : node.id)} className="flex w-full items-center gap-2 rounded-[5px] px-1.5 py-1.5 text-left transition-colors hover:bg-[var(--elevated)]"><span className="w-3 text-center text-[10px] text-[var(--text-tertiary)]">{expanded ? "▾" : "▸"}</span><span className="min-w-0 flex-1 truncate text-[10px] font-medium text-[var(--text-primary)]">{label}</span><code className="shrink-0 font-mono text-[9px] text-[var(--text-tertiary)]">{nodeId}</code></button>
                {expanded && <div className="ml-4 border-l border-[var(--border-subtle)] py-0.5 pl-1.5">{fields.length ? fields.map((field) => <ExpressionOption key={field} label={field} expression={`{{nodes.${nodeId}.${field}}}`} onClick={() => insert(`{{nodes.${nodeId}.${field}}}`)} />) : <p className="px-2 py-1 text-[9px] text-[var(--text-tertiary)]">No output fields defined for this node.</p>}</div>}
              </div>;
            })}</div>}
          </section>
        </div>
      </div>}
    </div>
  );
}
