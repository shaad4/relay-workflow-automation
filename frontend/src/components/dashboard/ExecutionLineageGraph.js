"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ExecutionRecoveryAction from "./ExecutionRecoveryAction";
import Pagination from "@/components/Pagination";
import { getExecutionAttempts } from "@/services/executions";
import { executionError, formatDuration, formatTime } from "@/lib/executions";
import {
  ExecutionIcon,
  ExecutionStatusBadge,
  executionButton,
  executionPanel,
} from "./ExecutionUI";

const branchColors = [
  "#d99a16",
  "#3b82f6",
  "#a78bfa",
  "#10b981",
  "#f472b6",
  "#f97316",
];

export default function ExecutionLineageGraph({
  execution,
  revision,
  onOpenRecovery,
}) {
  const [page, setPage] = useState(
    Math.max(1, Math.ceil((execution.attempt_number || 1) / 10)),
  );
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const rootId =
    execution.execution_group_id ||
    (!execution.replay_of_execution_id
      ? execution.id
      : result?.items[0]?.execution_group_id);
  useEffect(() => {
    const controller = new AbortController();
    getExecutionAttempts(execution.id, { page, signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) {
          setResult(data);
          setError(null);
        }
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(cause);
      });
    return () => controller.abort();
  }, [execution.id, page, retry, revision]);
  const items = result?.items || [];
  const graphWidth = Math.max(32, items.length * 14 + 12);
  const branchX = (index) => 8 + index * 14;
  const branchColor = (index) =>
    branchColors[
      (((result?.page || 1) - 1) * (result?.page_size || 10) + index) %
        branchColors.length
    ];
  function changePage(next) {
    setResult(null);
    setError(null);
    setPage(next);
  }
  return (
    <section
      className={`${executionPanel} execution-lineage-panel`}
      aria-labelledby="execution-lineage-title"
    >
      <div className="execution-lineage-heading">
        <div>
          <h2 id="execution-lineage-title">
            <ExecutionIcon type="history" />
            Replay history
          </h2>
          <p>Each colored branch connects a replay to its source attempt.</p>
        </div>
        {rootId && rootId !== execution.id && (
          <Link
            href={`/dashboard/executions/${encodeURIComponent(rootId)}`}
            className="execution-lineage-root-link"
          >
            View original <span aria-hidden="true">↗</span>
          </Link>
        )}
      </div>
      {error ? (
        <div role="alert" className="p-5 text-xs text-[var(--text-secondary)]">
          <p>{executionError(error)}</p>
          <button
            className={`${executionButton} mt-3`}
            onClick={() => {
              setError(null);
              setRetry((value) => value + 1);
            }}
          >
            Retry
          </button>
        </div>
      ) : !result ? (
        <div role="status" className="execution-lineage-loading">
          Loading replay history…
        </div>
      ) : (
        <>
          <div
            className="execution-replay-branches"
            style={{ "--branch-width": `${graphWidth}px` }}
          >
            <svg
              className="execution-replay-connectors"
              width={graphWidth}
              viewBox={`0 0 ${graphWidth} ${Math.max(1, items.length) * 64}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              {items.map((attempt, index) => {
                if (!attempt.replay_of_execution_id) return null;
                const parent = items.findIndex(
                  (item) => item.id === attempt.replay_of_execution_id,
                );
                const x = branchX(index);
                const y = index * 64 + 32;
                const parentX = parent < 0 ? x : branchX(parent);
                const parentY = parent < 0 ? 0 : parent * 64 + 32;
                return (
                  <path
                    key={attempt.id}
                    d={`M ${parentX} ${parentY} C ${x} ${parentY}, ${x} ${parentY + 16}, ${x} ${parentY + 24} L ${x} ${y}`}
                    fill="none"
                    stroke={branchColor(index)}
                    strokeWidth="2"
                    vectorEffect="non-scaling-stroke"
                    strokeDasharray={parent < 0 ? "4 3" : undefined}
                  />
                );
              })}
            </svg>
            <ol
              className="execution-replay-log"
              aria-label="Execution attempts in chronological order"
            >
              {result.items.map((attempt, index) => {
                const original =
                  attempt.id === rootId || !attempt.replay_of_execution_id;
                const number = (result.page - 1) * result.page_size + index;
                const current = attempt.id === execution.id;
                return (
                  <li key={attempt.id} className="execution-replay-entry">
                    <Link
                      href={`/dashboard/executions/${encodeURIComponent(attempt.id)}`}
                      aria-current={current ? "page" : undefined}
                      className={`execution-replay-row ${current ? "is-current" : ""}`}
                    >
                      <span
                        className="execution-replay-branch"
                        aria-hidden="true"
                      >
                        <span
                          className={`execution-replay-dot ${original ? "is-original" : ""}`}
                          style={{
                            left: `${branchX(index) - 5}px`,
                            "--branch-color": branchColor(index),
                          }}
                        />
                      </span>
                      <span className="execution-replay-name">
                        <strong>
                          {original ? "Original" : `Replay ${number}`}
                        </strong>
                        <code>{attempt.id.slice(0, 8)}</code>
                        {current && (
                          <span className="execution-lineage-viewing">
                            Viewing
                          </span>
                        )}
                        {attempt.replay_of_execution_id && (
                          <span className="execution-replay-source">
                            from {attempt.replay_of_execution_id.slice(0, 8)}
                          </span>
                        )}
                      </span>
                      <ExecutionStatusBadge status={attempt.status} />
                      <span className="execution-replay-time">
                        {formatTime(attempt.created_at)}
                      </span>
                      <span className="execution-replay-duration">
                        {formatDuration(attempt.duration_ms)}
                      </span>
                      <span
                        className="execution-replay-open"
                        aria-hidden="true"
                      >
                        ↗
                      </span>
                    </Link>
                    {onOpenRecovery && (
                      <ExecutionRecoveryAction
                        execution={attempt}
                        onOpen={onOpenRecovery}
                        compact
                      />
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
          {!result.items.length && (
            <p className="execution-lineage-loading">No attempts found.</p>
          )}
          {result.total > result.page_size && (
            <div className="execution-lineage-pagination">
              <Pagination
                page={result.page}
                pageSize={result.page_size}
                total={result.total}
                onPageChange={changePage}
              />
            </div>
          )}
        </>
      )}
    </section>
  );
}
