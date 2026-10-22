"use client";

import { useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import Pagination from "@/components/Pagination";
import DeadLetterDrawer from "@/components/dashboard/DeadLetterDrawer";
import { ExecutionCopyId, ExecutionIcon, ExecutionSkeleton, ExecutionStatusBadge, RefreshExecutions, executionButton, executionPanel } from "@/components/dashboard/ExecutionUI";
import { DeadLetterError } from "@/components/dashboard/DeadLetterUI";
import { getDeadLetterEvents } from "@/services/deadLetter";
import { deadLetterFilters, deadLetterMessage } from "@/lib/deadLetter";
import { formatTime, workflowName } from "@/lib/executions";

function DeadLetterList() {
  const [selectedId, setSelectedId] = useState(null);
  const changed = useRef(false);
  const heading = useRef(null);
  function closeDrawer() {
    setSelectedId(null);
    if (changed.current) { changed.current = false; refresh(); }
  }
  const [query, setQuery] = useState({ page: 1, status: "", revision: 0 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  function change(next) { setLoading(true); setError(null); setResult(null); setQuery(current => ({ ...current, ...next })); }
  const refresh = () => change({ revision: query.revision + 1 });
  useEffect(() => {
    document.title = "Dead-Letter Queue | Relay";
    const controller = new AbortController();
    getDeadLetterEvents({ status: query.status, limit: 10, offset: (query.page - 1) * 10, signal: controller.signal }).then(data => {
      if (controller.signal.aborted) return;
      const lastPage = Math.max(1, Math.ceil(data.total / 10));
      if (query.page > lastPage) { setQuery(current => ({ ...current, page: lastPage })); return; }
      setResult(data); setLoading(false);
    }).catch(cause => { if (!controller.signal.aborted) { setError(cause); setLoading(false); } });
    return () => controller.abort();
  }, [query]);
  return <DashboardShell pageTitle="Dead-Letter Queue"><div className="execution-workspace execution-history dlq-workspace">
    <header className="execution-page-header"><div className="execution-heading-group"><span className="execution-page-icon dlq-heading-icon"><ExecutionIcon type="alert" className="h-6 w-6"/></span><div><p className="execution-eyebrow">Review & recover</p><h1 ref={heading} tabIndex={-1}>Dead-Letter Queue</h1><p className="execution-header-description">Manage failed workflow executions and safely retry or resolve them.</p></div></div><RefreshExecutions busy={loading} onRefresh={refresh}/></header>
    <section className={executionPanel} aria-label="Dead-letter events" aria-busy={loading}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)] p-4"><div role="group" aria-label="Filter by status" className="execution-filter-tabs">{deadLetterFilters.map(([value, label]) => <button key={value} aria-pressed={query.status === value} onClick={() => change({ status: value, page: 1 })} className={`min-h-9 rounded-md px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--accent)] motion-reduce:transition-none ${query.status === value ? "bg-[var(--elevated)] text-[var(--text-primary)] shadow-sm ring-1 ring-[var(--border-default)]" : "text-[var(--text-secondary)] hover:bg-[var(--elevated)]"}`}>{value && <span className="dlq-filter-dot" data-status={value} aria-hidden="true"/>}{label}</button>)}</div><span role="status" className="text-xs text-[var(--text-secondary)]">{result ? `${result.total} records` : "Dead-letter events"}</span></div>
      {loading && <div className="p-4"><ExecutionSkeleton/></div>}
      {error && <div className="p-4"><DeadLetterError error={error} onRetry={refresh} busy={loading}/></div>}
      {result && <>{result.items.length ? <>
        <div className="hidden lg:block">
          <table className="execution-history-table dlq-history-table w-full table-fixed text-left text-xs">
            <caption className="sr-only">Failed workflow executions. Select an event to view its details.</caption>
            <thead className="border-b border-[var(--border-subtle)] text-[10px] uppercase tracking-wider text-[var(--text-secondary)]">
              <tr>{[["Workflow / execution", "w-[28%]"], ["Error message", "w-[23%]"], ["Attempts", "w-[9%]"], ["Status", "w-[15%]"], ["Created", "w-[19%]"], ["", "w-[6%]"]].map(([label, width]) => <th key={label} scope="col" className={`px-4 py-3 font-medium ${width}`}>{label || <span className="sr-only">View details</span>}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">{result.items.map(item => {
              const message = deadLetterMessage(item.error);
              return <tr key={item.id} onClick={event => { if (!event.target.closest("a, button") && !window.getSelection()?.toString()) setSelectedId(item.id); }} className="cursor-pointer hover:bg-[var(--elevated)]" data-status={item.status}>
                <td className="px-4 py-4"><div className="flex items-start gap-3"><span className="dlq-row-icon hidden xl:grid" data-status={item.status}><ExecutionIcon type={item.status === "resolved" ? "check" : item.status === "replayed" ? "replay" : "alert"}/></span><div className="min-w-0"><p className="mb-1.5 truncate text-xs font-medium" title={item.workflow_id ? workflowName(item) : "Workflow unavailable"}>{item.workflow_id ? workflowName(item) : "Workflow unavailable"}</p><div className="font-mono text-[10px] text-[var(--text-secondary)]"><ExecutionCopyId id={item.execution_id} shortened/></div></div></div></td>
                <td className="px-4 py-4"><p className="line-clamp-2 break-words text-xs leading-5 text-[var(--text-secondary)]" title={message}>{message}</p></td>
                <td className="px-4 py-4 font-mono text-[11px] tabular-nums text-[var(--text-secondary)]">{item.attempts}</td>
                <td className="px-4 py-4"><ExecutionStatusBadge status={item.status}/></td>
                <td className="px-4 py-4 text-[11px] leading-5 text-[var(--text-secondary)]">{formatTime(item.created_at)}</td>
                <td className="px-4 py-4"><button type="button" aria-haspopup="dialog" onClick={() => setSelectedId(item.id)} className="execution-row-action"><span aria-hidden="true">→</span><span className="sr-only">View details for {item.execution_id}</span></button></td>
              </tr>;
            })}</tbody>
          </table>
        </div>
        <div className="divide-y divide-[var(--border-subtle)] lg:hidden">{result.items.map(item => <article key={item.id} className="space-y-3 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><h2 className="mb-2 break-words text-sm font-medium">{item.workflow_id ? workflowName(item) : "Workflow unavailable"}</h2><div className="font-mono text-xs"><ExecutionCopyId id={item.execution_id} shortened/></div></div><ExecutionStatusBadge status={item.status}/></div>
          <p className="line-clamp-3 break-words text-xs leading-5 text-[var(--text-secondary)]">{deadLetterMessage(item.error)}</p>
          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-[var(--text-secondary)]"><span>{item.attempts} attempts</span><span>{formatTime(item.created_at)}</span></div>
          <button type="button" aria-haspopup="dialog" onClick={() => setSelectedId(item.id)} className="inline-flex min-h-9 items-center gap-2 rounded-md text-xs font-medium text-[var(--accent)] hover:underline focus-visible:outline-2 focus-visible:outline-[var(--accent)]">View Details <span aria-hidden="true">→</span><span className="sr-only"> for {item.execution_id}</span></button>
        </article>)}</div>
      </> : <div className="p-12 text-center"><h2 className="text-sm font-semibold">{query.status ? "No records match this status" : "No dead-letter events"}</h2><p className="mt-2 text-xs text-[var(--text-secondary)]">{query.status ? "Choose another status to find events." : "Failed workflow events will appear here when available."}</p>{query.status && <button onClick={() => change({ status: "", page: 1 })} className={`${executionButton} mt-4`}>Clear filter</button>}</div>}
      <footer className="border-t border-[var(--border-subtle)] px-4 py-3">{result.total > 10 ? <Pagination page={query.page} pageSize={10} total={result.total} onPageChange={page => change({ page })}/> : <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] text-[var(--text-secondary)]"><span>{result.total} records · Page 1 of 1</span><div className="flex gap-2"><button disabled className={executionButton}>Previous</button><button disabled className={executionButton}>Next</button></div></div>}</footer></>}
    </section><p className="text-xs text-[var(--text-secondary)]">Times shown in your local timezone</p>
    {selectedId && <DeadLetterDrawer key={selectedId} id={selectedId} onClose={closeDrawer} onChanged={() => { changed.current = true; }} fallbackFocusRef={heading}/>}
  </div></DashboardShell>;
}
export default function DeadLetterPage() { return <ProtectedRoute><DeadLetterList/></ProtectedRoute>; }
