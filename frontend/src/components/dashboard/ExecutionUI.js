"use client";

import Link from "next/link";
import ExecutionPayloadViewer from "./ExecutionPayloadViewer";
import { useState } from "react";
import { formatDuration, formatTime, normalizeStatus, statusLabel } from "@/lib/executions";

export const executionButton = "inline-flex min-h-9 items-center justify-center gap-2 rounded-md border border-[var(--border-default)] bg-[var(--surface)] px-3 py-2 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--elevated)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none";
export const executionPanel = "rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)]";

export function ExecutionIcon({ type = "generic", className = "h-4 w-4" }) {
  let path = <><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M8 12h8m-4-4v8"/></>;
  if (/webhook/.test(type)) path = <><circle cx="6" cy="16" r="3"/><circle cx="18" cy="16" r="3"/><circle cx="12" cy="5" r="3"/><path d="m10 7-3 6m7-6 3 6M9 16h6"/></>;
  else if (/schedule|clock/.test(type)) path = <><circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/></>;
  else if (/manual/.test(type)) path = <path d="m8 4 12 8-12 8Z"/>;
  else if (/http/.test(type)) path = <><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></>;
  else if (/email/.test(type)) path = <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 6 9 7 9-7"/></>;
  else if (/refund/.test(type)) path = <><path d="M4 10a8 8 0 1 1 2 8M4 4v6h6m5-2h-4a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4H9m3-10v12"/></>;
  else if (/rag|search/.test(type)) path = <><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6M7 10h6m-3-3v6"/></>;
  else if (/condition|decision/.test(type)) path = <><path d="m12 2 5 5-5 5-5-5 5-5Zm0 10v4M5 21v-5h14v5"/></>;
  else if (/approval/.test(type)) path = <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/></>;
  else if (/ai|generate/.test(type)) path = <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/></>;
  else if (type === "refresh") path = <><path d="M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 3M5 15a8 8 0 0 0 13 3"/></>;
  else if (type === "history") path = <><path d="M3 4v5h5M4 9a9 9 0 1 1 0 7M12 7v5l3 2"/></>;
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">{path}</svg>;
}

export function ExecutionStatusBadge({ status }) {
  const value = normalizeStatus(status);
  return <span className="relay-execution-status inline-flex max-w-full items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium" data-status={value}>
    <span key={value} className="relay-execution-status-change inline-flex items-center gap-1.5">
      {value === "completed" ? <span aria-hidden="true">✓</span> : value === "failed" || value === "dead_lettered" ? <span aria-hidden="true">×</span> : <span aria-hidden="true" className={`h-1.5 w-1.5 shrink-0 rounded-full bg-current ${value === "running" ? "motion-safe:animate-pulse" : ""}`}/>}
      {statusLabel(status)}
    </span>
  </span>;
}

export function RefreshExecutions({ busy, onRefresh }) {
  return <button type="button" disabled={busy} onClick={onRefresh} className={executionButton}><ExecutionIcon type="refresh" className={`h-4 w-4 ${busy ? "motion-safe:animate-spin" : ""}`}/>{busy ? "Refreshing…" : "Refresh"}</button>;
}

export function ExecutionSkeleton({ detail = false }) {
  return <div role="status" aria-label="Loading execution data" className="space-y-4"><span className="sr-only">Loading execution data</span>{detail && <div className={`${executionPanel} grid grid-cols-2 gap-6 p-6`}>{[0, 1, 2, 3].map(i => <div key={i} className="h-12 rounded bg-[var(--elevated)] motion-safe:animate-pulse"/>)}</div>}<div className={`${executionPanel} divide-y divide-[var(--border-subtle)]`}>{[0, 1, 2, 3, 4].map(i => <div key={i} className="flex gap-5 p-5"><div className="h-9 w-9 rounded-md bg-[var(--elevated)] motion-safe:animate-pulse"/><div className="flex-1 space-y-3"><div className="h-3 w-2/5 rounded bg-[var(--elevated)] motion-safe:animate-pulse"/><div className="h-2 w-1/4 rounded bg-[var(--elevated)] motion-safe:animate-pulse"/></div><div className="h-6 w-20 rounded bg-[var(--elevated)] motion-safe:animate-pulse"/></div>)}</div></div>;
}

export function ExecutionEmptyState({ filtered, onReset }) {
  return <section className="px-5 py-20 text-center"><div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl border border-[var(--border-default)] bg-[var(--canvas)] text-[var(--text-secondary)]"><ExecutionIcon type="history" className="h-6 w-6"/></div><h2 className="text-sm font-semibold">{filtered ? "No executions match this filter." : "No executions yet"}</h2><p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-[var(--text-secondary)]">{filtered ? "Choose another status to explore your workflow runs." : "Your workflow runs will appear here once a workflow is triggered."}</p>{filtered ? <button onClick={onReset} className={`${executionButton} mt-5`}>Clear filter</button> : <Link href="/workflows" className={`${executionButton} mt-5`}>Go to Workflows <span aria-hidden="true">→</span></Link>}</section>;
}

export function ExecutionErrorState({ message, notFound, onRetry, busy }) {
  return <div role="alert" className="rounded-lg border border-red-500/25 bg-red-500/5 p-5"><h2 className="text-sm font-semibold">{notFound ? "Execution not found" : "Unable to refresh executions"}</h2><p className="mt-1 text-xs leading-5 text-[var(--text-secondary)]">{message}</p>{!notFound && <button disabled={busy} onClick={onRetry} className={`${executionButton} mt-3`}>Try again</button>}</div>;
}

export function ExecutionField({ label, children, mono = false }) {
  return <div className="min-w-0"><dt className="text-[11px] text-[var(--text-secondary)]">{label}</dt><dd className={`mt-1.5 break-words text-xs leading-5 text-[var(--text-primary)] ${mono ? "font-mono [overflow-wrap:anywhere]" : ""}`}>{children ?? "—"}</dd></div>;
}

export function ExecutionCopyId({ id }) {
  const [message, setMessage] = useState("");
  async function copy() {
    try { await navigator.clipboard.writeText(id); setMessage("Copied"); }
    catch { setMessage("Couldn’t copy. Select the ID to copy it manually."); }
  }
  return <div><div className="flex items-start gap-2"><span className="min-w-0 select-all">{id}</span><button onClick={copy} className="shrink-0 rounded px-1 font-sans text-[var(--accent)] hover:underline focus-visible:outline-2 focus-visible:outline-[var(--accent)]" aria-label="Copy execution ID">Copy</button></div><span role="status" className="font-sans text-[11px] text-[var(--text-secondary)]">{message}</span></div>;
}

export function ExecutionStepTimeline({ steps }) {
  const maxDuration = Math.max(1, ...steps.map(step => step.duration_ms || 0));
  return <ol className="execution-timeline-list">{steps.map(step => <ExecutionStepItem key={step.id} step={step} maxDuration={maxDuration}/>)}</ol>;
}

function ExecutionStepItem({ step, maxDuration }) {
  const [open, setOpen] = useState(false);
  return <li className="execution-timeline-row">
    <div className="execution-step-rail" aria-hidden="true"><span className="execution-step-number">{String(step.sequence).padStart(2, "0")}</span><span className="execution-node-icon" data-type={step.node_type?.split(".")[0]}><ExecutionIcon type={step.node_type || "generic"} className="h-5 w-5"/></span></div>
    <details onToggle={event => setOpen(event.currentTarget.open)} className="relay-execution-step execution-step-content" data-status={normalizeStatus(step.status)}>
      <summary className="execution-step-summary">
        <div className="execution-step-title"><h3>{step.node_name || step.node_id}</h3><p>{step.node_type || "Unknown node type"}<span> · Attempt {step.attempt}</span></p></div>
        <div className="execution-step-duration"><span>{formatDuration(step.duration_ms)}</span><span className="execution-duration-track" aria-hidden="true"><i style={{ width: `${Math.max(3, (step.duration_ms || 0) / maxDuration * 100)}%` }}/></span></div>
        <ExecutionStatusBadge status={step.status}/><span className="relay-execution-chevron" aria-hidden="true">⌄</span>
      </summary>
      {open && <ExecutionPayloadViewer step={step}/>}
      <dl className="execution-step-inspector"><ExecutionField label="Node ID" mono>{step.node_id}</ExecutionField><ExecutionField label="Node type" mono>{step.node_type}</ExecutionField><ExecutionField label="Status">{statusLabel(step.status)}</ExecutionField><ExecutionField label="Sequence">{step.sequence}</ExecutionField><ExecutionField label="Attempt">{step.attempt}</ExecutionField><ExecutionField label="Duration">{formatDuration(step.duration_ms)}</ExecutionField><ExecutionField label="Started">{formatTime(step.started_at)}</ExecutionField><ExecutionField label="Completed">{formatTime(step.completed_at)}</ExecutionField></dl>
    </details>
  </li>;
}
