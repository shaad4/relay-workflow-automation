"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  formatDuration,
  formatTime,
  statusLabel,
  workflowName,
} from "@/lib/executions";
import { ExecutionIcon, ExecutionStatusBadge } from "./ExecutionUI";
import ExecutionAttemptHistory from "./ExecutionAttemptHistory";

export default function ExecutionHistoryTable({ items, revision }) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(new Set());
  function toggle(id) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  return (
    <table className="execution-history-table execution-group-table w-full table-fixed text-left text-xs">
      <caption className="sr-only">
        Workflow runs grouped with their replays. Status reflects the latest
        attempt.
      </caption>
      <thead>
        <tr>
          <th className="w-[30%]">Workflow / run</th>
          <th className="w-[18%]">Latest status</th>
          <th className="w-[15%]">Attempts</th>
          <th className="w-[21%]">Last activity</th>
          <th className="w-[10%]">Duration</th>
          <th className="w-[6%]">
            <span className="sr-only">View latest execution</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => {
          const groupId = item.execution_group_id;
          const open = expanded.has(groupId);
          const href = `/dashboard/executions/${encodeURIComponent(item.id)}`;
          return (
            <Fragment key={groupId}>
              <tr
                className={`execution-group-row cursor-pointer ${open ? "is-expanded" : ""}`}
                onClick={(event) => {
                  if (
                    event.target.closest("a, button") ||
                    window.getSelection()?.toString()
                  )
                    return;
                  router.push(href);
                }}
              >
                <td className="execution-group-name">
                  <div className="flex items-center gap-3">
                    <span className="execution-run-icon">
                      <ExecutionIcon type={item.trigger_type || "generic"} />
                    </span>
                    <div className="min-w-0">
                      <Link
                        href={href}
                        className="block truncate font-medium hover:underline"
                        title={workflowName(item)}
                      >
                        {workflowName(item)}
                      </Link>
                      <p className="mt-1.5 flex flex-wrap gap-2 text-[10px] text-[var(--text-secondary)]">
                        <code>{groupId.slice(0, 8)}</code>
                        <span>·</span>
                        <span>{statusLabel(item.trigger_type)}</span>
                      </p>
                    </div>
                  </div>
                </td>
                <td className="execution-group-status">
                  <ExecutionStatusBadge status={item.status} />
                </td>
                <td className="execution-group-attempts">
                  <button
                    type="button"
                    className="execution-attempt-toggle"
                    aria-expanded={open}
                    aria-controls={`attempts-${groupId}`}
                    onClick={() => toggle(groupId)}
                  >
                    <svg
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      aria-hidden="true"
                      className={open ? "rotate-90" : ""}
                    >
                      <path d="m6 4 4 4-4 4" />
                    </svg>
                    {item.attempt_count}{" "}
                    {item.attempt_count === 1 ? "attempt" : "attempts"}
                  </button>
                  {item.attempt_count > 1 && (
                    <span className="execution-replay-note">
                      Includes {item.attempt_count - 1}{" "}
                      {item.attempt_count === 2 ? "replay" : "replays"}
                    </span>
                  )}
                </td>
                <td className="execution-group-time">
                  {formatTime(item.created_at)}
                </td>
                <td className="execution-group-duration">
                  {formatDuration(item.duration_ms)}
                </td>
                <td className="execution-group-view">
                  <Link
                    href={href}
                    className="execution-row-action"
                    aria-label={`View latest execution for ${workflowName(item)}`}
                  >
                    <span aria-hidden="true">↗</span>
                  </Link>
                </td>
              </tr>
              {open && (
                <tr
                  id={`attempts-${groupId}`}
                  className="execution-group-expanded"
                >
                  <td colSpan={6}>
                    <ExecutionAttemptHistory
                      executionId={groupId}
                      revision={revision}
                    />
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
