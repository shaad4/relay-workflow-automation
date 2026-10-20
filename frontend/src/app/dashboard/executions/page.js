"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import Pagination from "@/components/Pagination";
import { getExecutions } from "@/services/executions";
import { executionError, executionFilters, formatDuration, formatTime, statusLabel, workflowName } from "@/lib/executions";
import { ExecutionEmptyState, ExecutionErrorState, ExecutionIcon, ExecutionSkeleton, ExecutionStatusBadge, RefreshExecutions, executionButton, executionPanel } from "@/components/dashboard/ExecutionUI";

function ExecutionHistory() {
  const router = useRouter();
  const [query, setQuery] = useState({ page: 1, status: "", revision: 0 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const refresh = () => { setLoading(true); setQuery(current => ({ ...current, revision: current.revision + 1 })); };
  function changeFilter(status) { setLoading(true); setResult(null); setQuery(current => ({ ...current, page: 1, status })); }
  function changePage(page) { setLoading(true); setResult(null); setQuery(current => ({ ...current, page })); }

  useEffect(() => {
    document.title = "Execution History | Relay";
    const controller = new AbortController();
    getExecutions({ page: query.page, pageSize: 10, status: query.status, signal: controller.signal }).then(data => {
      if (controller.signal.aborted) return;
      const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
      if (query.page > lastPage) { setQuery(current => ({ ...current, page: lastPage })); return; }
      setResult(data); setError(null); setUpdatedAt(new Date()); setLoading(false);
    }).catch(cause => { if (!controller.signal.aborted) { setError(cause); setLoading(false); } });
    return () => controller.abort();
  }, [query]);

  return <DashboardShell pageTitle="Executions"><div className="execution-workspace execution-history">
    <header className="execution-page-header"><div className="execution-heading-group"><span className="execution-page-icon"><ExecutionIcon type="history" className="h-6 w-6"/></span><div><p className="execution-eyebrow">Monitor & inspect</p><h1>Execution History</h1><p className="execution-header-description">Monitor workflow runs, track progress, and investigate failures.</p></div></div><RefreshExecutions busy={loading} onRefresh={refresh}/></header>

    <section className={executionPanel} aria-label="Execution history">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-subtle)] p-4"><div role="group" aria-label="Filter by execution status" className="execution-filter-tabs">{executionFilters.map(([value, label]) => <button key={value} aria-pressed={query.status === value} onClick={() => changeFilter(value)} className={`min-h-9 rounded-md px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--accent)] motion-reduce:transition-none ${query.status === value ? "bg-[var(--elevated)] text-[var(--text-primary)] shadow-sm ring-1 ring-[var(--border-default)]" : "text-[var(--text-secondary)] hover:bg-[var(--elevated)]"}`}>{label}</button>)}</div><span className="text-[11px] tabular-nums text-[var(--text-secondary)]" role="status">{result ? `${result.total.toLocaleString()} executions` : "Execution history"}</span></div>
      {error && <div className="p-4"><ExecutionErrorState message={executionError(error)} onRetry={refresh} busy={loading}/></div>}
      {loading && !result ? <div className="p-4"><ExecutionSkeleton/></div> : result && <div aria-busy={loading}>
        {result.items.length === 0 ? <ExecutionEmptyState filtered={Boolean(query.status)} onReset={() => changeFilter("")}/> : <>
          <div className="hidden md:block"><table className="execution-history-table w-full table-fixed text-left text-xs"><caption className="sr-only">Workflow executions. Select an execution to view its steps.</caption><thead className="border-b border-[var(--border-subtle)] text-[10px] uppercase tracking-wider text-[var(--text-secondary)]"><tr>{["Workflow", "Status", "Trigger", "Started", "Duration", ""].map((name, i) => <th key={i} scope="col" className={`px-4 py-3 font-medium ${i === 0 ? "w-[28%]" : i === 1 ? "w-[19%]" : i === 3 ? "w-[21%]" : i === 5 ? "w-12" : ""}`}>{name || <span className="sr-only">View details</span>}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border-subtle)]">{result.items.map(item => <tr key={item.id} onClick={event => { if (!event.target.closest("a") && !window.getSelection()?.toString()) router.push(`/dashboard/executions/${encodeURIComponent(item.id)}`); }} className="cursor-pointer hover:bg-[var(--elevated)]"><td className="px-4 py-4"><div className="flex items-center gap-3"><span className="hidden h-9 w-9 shrink-0 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--canvas)] text-[var(--text-secondary)] xl:grid"><ExecutionIcon type={item.trigger_type || "generic"}/></span><div className="min-w-0"><Link href={`/dashboard/executions/${encodeURIComponent(item.id)}`} className="block truncate font-medium hover:text-[var(--accent)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]" title={workflowName(item)}>{workflowName(item)}</Link><span className="mt-1 block font-mono text-[10px] text-[var(--text-secondary)]">{item.id.slice(0, 8)}</span></div></div></td><td className="px-4 py-4"><ExecutionStatusBadge status={item.status}/></td><td className="px-4 py-4 text-[var(--text-secondary)]">{statusLabel(item.trigger_type)}</td><td className="px-4 py-4 text-[11px] leading-5 text-[var(--text-secondary)]">{formatTime(item.started_at)}</td><td className="px-4 py-4 font-mono text-[11px] text-[var(--text-secondary)]">{formatDuration(item.duration_ms)}</td><td className="px-4 py-4 text-[var(--text-secondary)]" aria-hidden="true">→</td></tr>)}</tbody></table></div>
          <div className="divide-y divide-[var(--border-subtle)] md:hidden">{result.items.map(item => <Link key={item.id} href={`/dashboard/executions/${encodeURIComponent(item.id)}`} className="block space-y-3 p-4 hover:bg-[var(--elevated)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]"><div className="flex flex-wrap items-start justify-between gap-2"><div className="min-w-0 flex-1"><h2 className="break-words text-sm font-medium">{workflowName(item)}</h2><p className="mt-1 font-mono text-[10px] text-[var(--text-secondary)]">{item.id.slice(0, 8)}</p></div><ExecutionStatusBadge status={item.status}/></div><div className="flex justify-between gap-2 text-xs text-[var(--text-secondary)]"><span>{statusLabel(item.trigger_type)}</span><span>{formatDuration(item.duration_ms)} <span aria-hidden="true">→</span></span></div><p className="text-[11px] text-[var(--text-secondary)]">{formatTime(item.started_at)}</p></Link>)}</div>
        </>}
        <footer className="border-t border-[var(--border-subtle)] px-4 py-3">{result.total > result.page_size ? <div className={loading ? "pointer-events-none opacity-50" : ""} inert={loading ? true : undefined}><Pagination page={result.page} pageSize={result.page_size} total={result.total} onPageChange={changePage}/></div> : <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] text-[var(--text-secondary)]"><span>{result.total} executions · Page 1 of 1</span><div className="flex gap-2"><button disabled className={executionButton}>Previous</button><button disabled className={executionButton}>Next</button></div></div>}</footer>
      </div>}
    </section>
    {updatedAt && <p className="text-[11px] text-[var(--text-secondary)]">Last refreshed {formatTime(updatedAt)} · Times shown in your local timezone</p>}
  </div></DashboardShell>;
}

export default function ExecutionsPage() { return <ProtectedRoute><ExecutionHistory/></ProtectedRoute>; }
