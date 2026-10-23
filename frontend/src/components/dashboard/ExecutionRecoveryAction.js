"use client";

export default function ExecutionRecoveryAction({ execution, onOpen, compact = false }) {
  if (!execution.dead_letter_event_id) return null;
  const pending = execution.recovery_status === "pending";
  const label = pending ? "Needs attention" : execution.recovery_status === "replayed" ? "Replayed" : execution.recovery_status === "resolved" ? "Resolved" : "Recovery recorded";
  return <span className={`execution-recovery-action ${compact ? "is-compact" : ""}`}>
    <span className="execution-recovery-state">{label}</span>
    <button type="button" onClick={() => onOpen(execution.dead_letter_event_id)}>{pending ? "Review failure" : "View recovery details"}<span aria-hidden="true"> →</span></button>
  </span>;
}
