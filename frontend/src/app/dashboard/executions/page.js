"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import Pagination from "@/components/Pagination";
import ExecutionHistoryTable from "@/components/dashboard/ExecutionHistoryTable";
import { getExecutionGroups } from "@/services/executions";
import { executionError, executionFilters, formatTime } from "@/lib/executions";
import { ExecutionEmptyState, ExecutionErrorState, ExecutionIcon, ExecutionSkeleton, RefreshExecutions, executionButton, executionPanel } from "@/components/dashboard/ExecutionUI";

function ExecutionHistory() {
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
    getExecutionGroups({ page: query.page, pageSize: 10, status: query.status, signal: controller.signal }).then(data => {
      if (controller.signal.aborted) return;
      const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
      if (query.page > lastPage) { setQuery(current => ({ ...current, page: lastPage })); return; }
      setResult(data); setError(null); setUpdatedAt(new Date()); setLoading(false);
    }).catch(cause => { if (!controller.signal.aborted) { setError(cause); setLoading(false); } });
    return () => controller.abort();
  }, [query]);

  return <DashboardShell pageTitle="Executions"><div className="execution-workspace execution-history">
    <header className="execution-page-header"><div className="execution-heading-group"><span className="execution-page-icon"><ExecutionIcon type="history" className="h-6 w-6"/></span><div><p className="execution-eyebrow">Monitor & inspect</p><h1>Execution History</h1><p className="execution-header-description">Original runs and their replays, together. Expand a run to inspect every attempt.</p></div></div><RefreshExecutions busy={loading} onRefresh={refresh}/></header>

    <section className={executionPanel} aria-label="Execution history">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-subtle)] p-4"><div role="group" aria-label="Filter by execution status" className="execution-filter-tabs">{executionFilters.map(([value, label]) => <button key={value} aria-pressed={query.status === value} onClick={() => changeFilter(value)} className={`min-h-9 rounded-md px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--accent)] motion-reduce:transition-none ${query.status === value ? "bg-[var(--elevated)] text-[var(--text-primary)] shadow-sm ring-1 ring-[var(--border-default)]" : "text-[var(--text-secondary)] hover:bg-[var(--elevated)]"}`}>{label}</button>)}</div><span className="text-[11px] tabular-nums text-[var(--text-secondary)]" role="status">{result ? `${result.total.toLocaleString()} runs` : "Execution history"}</span></div>
      {error && <div className="p-4"><ExecutionErrorState message={executionError(error)} onRetry={refresh} busy={loading}/></div>}
      {loading && !result ? <div className="p-4"><ExecutionSkeleton/></div> : result && <div aria-busy={loading}>
        {result.items.length === 0 ? <ExecutionEmptyState filtered={Boolean(query.status)} onReset={() => changeFilter("")}/> : <ExecutionHistoryTable items={result.items} revision={query.revision}/>}

        <footer className="border-t border-[var(--border-subtle)] px-4 py-3">{result.total > result.page_size ? <div className={loading ? "pointer-events-none opacity-50" : ""} inert={loading ? true : undefined}><Pagination page={result.page} pageSize={result.page_size} total={result.total} onPageChange={changePage}/></div> : <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] text-[var(--text-secondary)]"><span>{result.total} runs · Page 1 of 1</span><div className="flex gap-2"><button disabled className={executionButton}>Previous</button><button disabled className={executionButton}>Next</button></div></div>}</footer>
      </div>}
    </section>
    <p className="execution-history-hint"><ExecutionIcon type="history"/>Status filters apply to the latest attempt in each run. Earlier failures remain in its attempt history.</p>
    {updatedAt && <p className="text-[11px] text-[var(--text-secondary)]">Last refreshed {formatTime(updatedAt)} · Times shown in your local timezone</p>}
  </div></DashboardShell>;
}

export default function ExecutionsPage() { return <ProtectedRoute><ExecutionHistory/></ProtectedRoute>; }
