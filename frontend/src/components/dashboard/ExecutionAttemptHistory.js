"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Pagination from "@/components/Pagination";
import { getExecutionAttempts } from "@/services/executions";
import { executionError, formatDuration, formatTime } from "@/lib/executions";
import { ExecutionStatusBadge, executionButton } from "./ExecutionUI";

export default function ExecutionAttemptHistory({ executionId, currentId, revision = 0 }) {
  const [page, setPage] = useState(1);
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    getExecutionAttempts(executionId, { page, signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) { setResult(data); setError(null); }
    }).catch(cause => { if (!controller.signal.aborted) setError(cause); });
    return () => controller.abort();
  }, [executionId, page, retry, revision]);
  function changePage(next) { setResult(null); setError(null); setPage(next); }
  if (error) return <div role="alert" className="execution-attempt-error"><p>{executionError(error)}</p><button className={`${executionButton} mt-3`} onClick={() => { setError(null); setResult(null); setRetry(value => value + 1); }}>Retry</button></div>;
  if (!result) return <div role="status" className="execution-attempt-loading"><span className="execution-loading-dot"/>Loading related attempts…</div>;
  return <div className="execution-attempt-history">
    <div className="execution-attempt-heading"><span>Attempt history</span><span>{result.total} {result.total === 1 ? "attempt" : "attempts"} · oldest first</span></div>
    <ol start={(page - 1) * 10 + 1} className="execution-attempt-list">{result.items.map((item, index) => {
      const number = (page - 1) * 10 + index + 1;
      return <li key={item.id} className={item.id === currentId ? "is-current" : ""}>
        <span className="execution-attempt-number" aria-hidden="true">{String(number).padStart(2, "0")}</span>
        <div className="execution-attempt-info"><Link href={`/dashboard/executions/${encodeURIComponent(item.id)}`} className="execution-attempt-link">{item.replay_of_execution_id ? `Replay ${number - 1}` : "Original execution"}<span aria-hidden="true">↗</span></Link><span className="execution-attempt-meta"><code>{item.id.slice(0, 8)}</code><span>·</span>{formatTime(item.created_at)}{item.id === currentId && <span className="execution-current-label">Viewing</span>}</span>{item.replay_of_execution_id && <span className="execution-attempt-parent">Replayed from <code>{item.replay_of_execution_id.slice(0, 8)}</code></span>}</div>
        <div className="execution-attempt-outcome"><ExecutionStatusBadge status={item.status}/><span>{formatDuration(item.duration_ms)}</span></div>
      </li>;
    })}</ol>
    {!result.items.length && <p className="p-4 text-xs text-[var(--text-secondary)]">No attempts recorded.</p>}
    {result.total > result.page_size && <Pagination page={result.page} pageSize={result.page_size} total={result.total} onPageChange={changePage}/>}
  </div>;
}
