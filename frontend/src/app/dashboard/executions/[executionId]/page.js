"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import { DeadLetterConfirmation } from "@/components/dashboard/DeadLetterUI";
import DeadLetterDrawer from "@/components/dashboard/DeadLetterDrawer";
import ExecutionRecoveryAction from "@/components/dashboard/ExecutionRecoveryAction";
import ExecutionLineageGraph from "@/components/dashboard/ExecutionLineageGraph";
import DashboardShell from "@/components/dashboard/DashboardShell";
import { cancelExecution, getExecutionDetails, getExecutionSteps } from "@/services/executions";
import { executionError, formatDuration, formatTime, normalizeStatus, pollingDelay, statusLabel, workflowName } from "@/lib/executions";
import { ExecutionIcon, ExecutionCopyId, ExecutionErrorState, ExecutionField, ExecutionSkeleton, ExecutionStatusBadge, ExecutionStepTimeline, RefreshExecutions, executionPanel, executionButton } from "@/components/dashboard/ExecutionUI";

function ExecutionDetail({ executionId }) {
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelRequested, setCancelRequested] = useState(false);
  const [cancelNotice, setCancelNotice] = useState(null);
  const [pollingStopped, setPollingStopped] = useState(false);
  const cancellation = useRef({ locked: false, requested: false, polls: 0, terminal: false });
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [recoveryId, setRecoveryId] = useState(null);
  const recoveryFocus = useRef(null);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const refreshRef = useRef(null);
  const refresh = useCallback(() => refreshRef.current?.(), []);

  useEffect(() => {
    let disposed = false;
    let inFlight = false;
    let timer;
    let controller;
    let lastStatus;
    async function load() {
      if (disposed || inFlight) return;
      clearTimeout(timer);
      inFlight = true;
      setBusy(true);
      controller = new AbortController();
      let delay = null;
      try {
        // Wait for both requests to settle before scheduling another refresh.
        const responses = await Promise.allSettled([
          getExecutionDetails(executionId, { signal: controller.signal }),
          getExecutionSteps(executionId, { signal: controller.signal }),
        ]);
        if (disposed) return;
        if (responses[0].status === "fulfilled") lastStatus = responses[0].value.status;
        const failure = responses.find(response => response.status === "rejected");
        if (failure) throw failure.reason;
        const execution = responses[0].value;
        if (cancellation.current.terminal) execution.status = "cancelled";
        if (execution.cancel_requested_at) cancellation.current.requested = true;
        if (normalizeStatus(execution.status) === "cancelled") {
          if (cancellation.current.requested) setCancelNotice({ message: "Execution cancelled." });
          window.dispatchEvent(new Event("relay:approvals-updated"));
        }
        setData({ execution, steps: responses[1].value.items });
        setUpdatedAt(new Date()); setError(null);
        document.title = `${workflowName(execution)} · Execution | Relay`;
        delay = pollingDelay(execution.status);
      } catch (cause) {
        if (disposed) return;
        setError(cause);
        if (![401, 403, 404].includes(cause.status)) delay = pollingDelay(lastStatus);
      } finally {
        inFlight = false;
        if (!disposed) {
          setBusy(false);
          if (cancellation.current.requested && delay !== null) {
            cancellation.current.polls += 1;
            delay = cancellation.current.polls < 75 ? 4000 : null;
            setPollingStopped(delay === null);
          }
          if (delay !== null) timer = setTimeout(load, delay);
        }
      }
    }
    refreshRef.current = load;
    load();
    return () => { disposed = true; clearTimeout(timer); controller?.abort(); refreshRef.current = null; };
  }, [executionId]);

  async function submitCancellation() {
    if (!["pending", "running", "waiting_for_approval"].includes(normalizeStatus(data?.execution.status)) || cancellation.current.locked || cancellation.current.requested || cancellation.current.terminal) return;
    cancellation.current.locked = true;
    setCancelling(true); setCancelNotice(null);
    try {
      const result = await cancelExecution(executionId);
      if (!mounted.current) return;
      if (!["cancelled", "already_cancelled", "cancellation_requested"].includes(result.status)) throw new Error("Unexpected cancellation response");
      const requested = result.status === "cancellation_requested";
      cancellation.current.requested = requested;
      cancellation.current.terminal = !requested;
      setCancelRequested(requested);
      if (!requested) setData(current => current && ({ ...current, execution: { ...current.execution, status: "cancelled" } }));
      setCancelNotice({ message: requested ? "Cancellation requested" : "Execution cancelled." });
      setConfirmCancel(false);
      window.dispatchEvent(new Event("relay:approvals-updated"));
      refresh();
    } catch (cause) {
      if (!mounted.current) return;
      setCancelNotice({ error: true, message: cause.status === 404 ? "Execution not found or unavailable." : cause.status === 409 ? "This execution can no longer be cancelled." : "Unable to cancel execution. Please try again." });
      setConfirmCancel(false);
      if (cause.status === 409) refresh();
    } finally {
      cancellation.current.locked = false;
      if (mounted.current) setCancelling(false);
    }
  }

  const execution = data?.execution;
  const steps = data?.steps || [];
  const completed = steps.filter(step => normalizeStatus(step.status) === "completed").length;
  const active = execution && pollingDelay(execution.status) !== null;
  const notFound = error?.status === 404;
  const state = normalizeStatus(execution?.status);
  const cancellable = ["pending", "running", "waiting_for_approval"].includes(state);
  const requested = cancellable && (cancelRequested || Boolean(execution?.cancel_requested_at));
  const updateLabel = pollingStopped && cancellable ? "Automatic updates paused. Refresh to check cancellation." : error ? "Updates interrupted" : state === "waiting_for_approval" && !requested ? "Updates every 30 seconds" : active ? "Live updates every 4 seconds" : "Auto-refresh off";
  return <DashboardShell pageTitle="Execution details"><div className="execution-workspace">
    <nav ref={recoveryFocus} tabIndex={-1} className="execution-breadcrumb" aria-label="Breadcrumb"><Link href="/dashboard/executions">Executions</Link><span aria-hidden="true">/</span><span className="font-mono">{executionId.slice(0, 8)}</span></nav>
    <header className="execution-page-header"><div className="execution-heading-group"><span className="execution-page-icon"><ExecutionIcon type="history" className="h-6 w-6"/></span><div className="min-w-0"><p className="execution-eyebrow">{execution ? execution.replay_of_execution_id ? `Replay${execution.attempt_number ? ` ${execution.attempt_number - 1}` : ""}` : "Original execution" : "Workflow run"}</p><h1>{execution ? workflowName(execution) : "Workflow execution"}</h1><p className="execution-header-description">{execution ? `${execution.replay_of_execution_id ? "Replayed from a failed step" : `Triggered by ${statusLabel(execution.trigger_type).toLowerCase()}`} · ${formatTime(execution.started_at)}` : "Inspect the progress and outcome of this run."}</p></div></div><div className="flex flex-wrap items-center gap-2">{cancellable && !notFound && <button type="button" className={executionButton} disabled={cancelling || requested} onClick={() => setConfirmCancel(true)}>{requested ? "Cancellation requested" : "Cancel"}</button>}<RefreshExecutions busy={busy} onRefresh={refresh}/></div></header>
    {cancelNotice && <p role={cancelNotice.error ? "alert" : "status"} className="text-sm text-[var(--text-secondary)]">{cancelNotice.message}</p>}
    {error && <ExecutionErrorState message={executionError(error)} notFound={notFound} onRetry={refresh} busy={busy}/>}
    {!data && busy && <ExecutionSkeleton detail/>}
    {execution && !notFound && <>
      <section className="execution-metrics" aria-label="Run summary">
        <div><span className="execution-metric-label">This attempt</span><ExecutionStatusBadge status={requested ? "cancellation_requested" : execution.status}/><ExecutionRecoveryAction execution={execution} onOpen={setRecoveryId}/><p>{requested ? "Waiting for cancellation to take effect" : state === "cancelled" ? "Workflow cancelled" : state === "completed" ? "Workflow completed successfully" : state === "failed" ? "Review the failed step below" : state === "waiting_for_approval" ? "Waiting for a human decision" : active ? "Execution in progress" : "Latest recorded status"}</p></div>
        <div><span className="execution-metric-label">Total duration</span><strong className="font-mono">{formatDuration(execution.duration_ms)}</strong><p>Elapsed execution time</p></div>
        <div><span className="execution-metric-label">Steps completed</span><strong>{completed}<span className="execution-metric-denominator"> / {steps.length}</span></strong><p>Of all recorded steps</p></div>
        <div><span className="execution-metric-label">Started by</span><strong className="execution-trigger-value"><ExecutionIcon type={execution.replay_of_execution_id ? "replay" : execution.trigger_type || "generic"}/>{execution.replay_of_execution_id ? "Replay" : statusLabel(execution.trigger_type)}</strong><p>{execution.replay_of_execution_id ? "Resumed from the failed step" : "How this run started"}</p></div>
      </section>

      <div className="execution-detail-grid">
        <div className="min-w-0 space-y-5">
          <section className={`${executionPanel} execution-timeline-panel`} aria-labelledby="execution-timeline">
            <div className="execution-panel-heading"><div><h2 id="execution-timeline">Execution timeline</h2><p>Every step, from trigger to outcome.</p></div><span className="execution-record-count">{steps.length} steps</span></div>
            <div className="execution-progress-strip" aria-label={`${completed} of ${steps.length} recorded steps completed`}>{steps.map(step => <span key={step.id} data-status={normalizeStatus(step.status)} title={`${step.node_name || step.node_id}: ${statusLabel(step.status)}`}/>)}</div>
            <div className="execution-timeline-caption"><span>Step / action</span><span>Duration</span><span>Status</span><span aria-hidden="true"/></div>
            {steps.length > 0 ? <ExecutionStepTimeline steps={steps}/> : <div className="px-5 py-12 text-center"><h3 className="text-sm font-medium">No steps recorded yet</h3><p className="mt-2 text-xs text-[var(--text-secondary)]">{active ? "Steps will appear here as this execution progresses." : "No step history is available for this execution."}</p></div>}
            <div className="execution-timeline-footer"><span className={`execution-update-dot ${active && !error && !pollingStopped ? "is-live" : ""}`} aria-hidden="true"/><span role="status">{updateLabel}</span><span className="ml-auto">Expand a step to inspect</span></div>
          </section>
          {execution.error && <section className="rounded-lg border border-red-500/25 bg-red-500/5 p-5" aria-labelledby="execution-error"><div className="execution-error-heading"><h2 id="execution-error" className="text-sm font-semibold">Execution error</h2><ExecutionRecoveryAction execution={execution} onOpen={setRecoveryId}/></div><p className="mt-1 text-xs text-[var(--text-secondary)]">Error information reported for this run.</p><pre className="mt-4 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-md border border-red-500/15 bg-[var(--canvas)] p-4 font-mono text-xs leading-6">{JSON.stringify(execution.error, null, 2)}</pre></section>}
        </div>
        <aside className={`${executionPanel} execution-run-details`} aria-labelledby="run-details"><div className="execution-panel-heading"><h2 id="run-details">Run details</h2><ExecutionIcon type="generic"/></div><dl className="execution-metadata"><ExecutionField label="Execution ID" mono><ExecutionCopyId id={execution.id}/></ExecutionField><ExecutionField label="Workflow">{workflowName(execution)}</ExecutionField><ExecutionField label="Started">{formatTime(execution.started_at)}</ExecutionField><ExecutionField label="Completed">{formatTime(execution.completed_at)}</ExecutionField><ExecutionField label="Workflow ID" mono>{execution.workflow_id}</ExecutionField><ExecutionField label="Version ID" mono>{execution.workflow_version_id}</ExecutionField></dl><div className="execution-metadata-footer"><ExecutionIcon type="clock"/><span>Times shown in your local timezone</span></div></aside>
      </div>
      <ExecutionLineageGraph key={executionId} execution={execution} revision={updatedAt?.getTime()} onOpenRecovery={setRecoveryId}/>
      <p className="execution-last-updated">Last refreshed {formatTime(updatedAt)}</p>
    </>}
    {confirmCancel && <DeadLetterConfirmation action="cancel" busy={cancelling} title="Cancel workflow execution?" description="This will stop the workflow from starting additional steps. Actions already completed cannot be undone. An action currently running may finish before cancellation takes effect." cancelLabel="Keep Running" confirmLabel="Cancel Execution" onClose={() => setConfirmCancel(false)} onConfirm={submitCancellation}/>}
    {recoveryId && <DeadLetterDrawer key={recoveryId} id={recoveryId} onClose={() => setRecoveryId(null)} onChanged={refresh} fallbackFocusRef={recoveryFocus}/> }
  </div></DashboardShell>;

}

export default function ExecutionDetailPage() {
  const { executionId } = useParams();
  return <ProtectedRoute><ExecutionDetail key={executionId} executionId={executionId}/></ProtectedRoute>;
}
