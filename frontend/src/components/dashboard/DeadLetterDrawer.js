"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ExecutionCopyId, ExecutionField, ExecutionIcon, ExecutionSkeleton, ExecutionStatusBadge, RefreshExecutions, executionAction } from "@/components/dashboard/ExecutionUI";
import ExecutionAttemptHistory from "./ExecutionAttemptHistory";
import { DeadLetterConfirmation, DeadLetterError } from "@/components/dashboard/DeadLetterUI";
import { getDeadLetterEvent, replayDeadLetterEvent, resolveDeadLetterEvent } from "@/services/deadLetter";
import { deadLetterMessage } from "@/lib/deadLetter";
import { formatTime, workflowName } from "@/lib/executions";

export default function DeadLetterDrawer({ id, onClose, onChanged, fallbackFocusRef }) {
  const dialog = useRef(null);
  const closeButton = useRef(null);
  const resolveButton = useRef(null);
  const [replayRejected, setReplayRejected] = useState(false);
  const [showAttempts, setShowAttempts] = useState(false);
  const [historyRevision, setHistoryRevision] = useState(0);
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [action, setAction] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [notice, setNotice] = useState(null);
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const request = useRef(null);
  const locked = useRef(false);
  const mounted = useRef(false);
  const refresh = useCallback(() => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    return getDeadLetterEvent(id, { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) { setEvent(data); setNeedsRefresh(false); setError(null); }
    }).catch(cause => {
      if (!controller.signal.aborted) { setError(cause); setNeedsRefresh(true); }
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
  }, [id]);
  useEffect(() => {
    mounted.current = true;
    refresh();
    return () => { mounted.current = false; request.current?.abort(); };
  }, [refresh]);

  useEffect(() => {
    const previous = document.activeElement;
    const element = dialog.current;
    const fallback = fallbackFocusRef.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    closeButton.current?.focus();
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
      if (previous?.isConnected) previous.focus();
      else fallback?.focus();
    };
  }, [fallbackFocusRef]);

  useEffect(() => {
    if (replayRejected && !processing && !action) resolveButton.current?.focus();
  }, [replayRejected, processing, action]);

  function reload() { setLoading(true); setHistoryRevision(value => value + 1); refresh(); }

  async function confirm() {
    if (locked.current || event?.status !== "pending" || needsRefresh || loading || (action === "replay" && replayRejected)) return;
    locked.current = true; setProcessing(true); setActionError(null); setNotice(null);
    try {
      const result = await (action === "replay" ? replayDeadLetterEvent(id) : resolveDeadLetterEvent(id));
      if (!mounted.current) return;
      setNeedsRefresh(true);
      setEvent(current => ({ ...current, status: action === "replay" ? "replayed" : "resolved", resolved_at: result.resolved_at ?? current.resolved_at }));
      setNotice(action === "replay" ? { message: "Replay accepted. A new execution has been queued.", executionId: result.execution_id } : { message: "Dead-letter event marked as resolved." });
      setShowAttempts(true);
      setHistoryRevision(value => value + 1);
      onChanged();
      setAction(null);
      setLoading(true);
      await refresh();
    } catch (cause) {
      if (!mounted.current) return;
      if (action === "replay" && cause.status === 422) {
        // A rejected replay did not create an execution; resolving remains valid.
        setReplayRejected(true);
        setAction(null);
        setActionError(null);
        setError(null);
        setNeedsRefresh(false);
        return;
      }
      setActionError(cause); setNeedsRefresh(true);
      // A failed response can leave the mutation outcome unknown. Require a
      // successful refresh before another action; never automatically retry POST.
      setError(cause);
    } finally {
      locked.current = false;
      if (mounted.current) setProcessing(false);
    }
  }
  const disabled = processing || loading || needsRefresh || Boolean(error) || event?.status !== "pending";
  return <dialog ref={dialog} aria-labelledby="dlq-drawer-title" aria-describedby="dlq-drawer-description"
    onCancel={event => { if (event.target !== event.currentTarget) return; event.preventDefault(); if (!processing && !action) onClose(); }}
    onClick={event => { if (event.target === event.currentTarget && !processing && !action) { const bounds = event.currentTarget.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose(); } }}
    className="dlq-drawer">
    <div className="dlq-drawer-layout">
      <header className="dlq-drawer-header">
        <div className="dlq-drawer-title"><span className="dlq-heading-icon"><ExecutionIcon type="alert" className="h-5 w-5"/></span><div><p>Dead-Letter Queue</p><h2 id="dlq-drawer-title">Failure details</h2></div></div>
        <div className="flex items-center gap-2"><RefreshExecutions busy={loading || processing} onRefresh={reload}/><button ref={closeButton} type="button" disabled={processing} onClick={onClose} className="execution-icon-button" aria-label="Close event details"><ExecutionIcon type="close"/></button></div>
      </header>
      <div className="dlq-drawer-body">
        <p id="dlq-drawer-description" className="dlq-description">Review what went wrong and choose how to recover.</p>
        {notice && <div role="status" className="dlq-notice"><ExecutionIcon type="check"/><div><p>{notice.message}</p>{notice.executionId && <Link href={`/dashboard/executions/${encodeURIComponent(notice.executionId)}`} className="execution-text-link">View replay execution <span aria-hidden="true">↗</span></Link>}</div></div>}
        {replayRejected && event?.status === "pending" && <div role="alert" className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4"><h3 className="flex items-center gap-2 text-sm font-semibold text-amber-800 dark:text-amber-300"><ExecutionIcon type="alert"/>Replay unavailable</h3><p className="mt-2 text-xs leading-6 text-[var(--text-secondary)]">Relay could not approve a safe replay. No new execution was created. Review the failure, then choose <strong className="text-[var(--text-primary)]">Mark resolved</strong> once you’ve handled it. This closes the event without running it again.</p></div>}
        {error && <DeadLetterError error={error} onRetry={reload} busy={loading || processing}/>}
        {loading && !event && <ExecutionSkeleton detail/>}
        {event && error?.status !== 404 && <>
          <section className="dlq-state-summary" aria-label="Event status"><ExecutionStatusBadge status={event.status}/><p>{event.status === "pending" ? (replayRejected ? "Awaiting resolution. Mark this event as resolved once the failure has been handled." : "Needs attention. Replay the failed step or mark this event as handled.") : event.status === "replayed" ? "A replay was accepted. Check its attempt history for the execution outcome." : "This event was marked as handled. No further action is needed."}</p></section>
          <section className="dlq-failure-card" aria-labelledby="dlq-failure"><div className="dlq-section-heading"><ExecutionIcon type="alert"/><h3 id="dlq-failure">Failure reason</h3></div><p className="dlq-error-message">{deadLetterMessage(event.error)}</p><dl className="space-y-4">{event.failed_node_name && <ExecutionField label="Failed node">{event.failed_node_name}</ExecutionField>}<ExecutionField label="Failed node type" mono>{event.failed_node_type || "Not recorded"}</ExecutionField><ExecutionField label="Failed step ID" mono>{event.execution_step_id}</ExecutionField></dl></section>
          <section className="dlq-inspector-section" aria-labelledby="dlq-overview"><div className="dlq-section-heading"><h3 id="dlq-overview">Execution information</h3><Link href={`/dashboard/executions/${encodeURIComponent(event.execution_id)}`} className="execution-text-link">Open execution <span aria-hidden="true">↗</span></Link></div><dl className="dlq-metadata"><ExecutionField label="Workflow">{event.workflow_id ? <Link href={`/workflows/${encodeURIComponent(event.workflow_id)}`} className="execution-text-link">{workflowName(event)}<span aria-hidden="true">↗</span></Link> : "Workflow unavailable"}</ExecutionField><ExecutionField label="Execution ID" mono><ExecutionCopyId id={event.execution_id}/></ExecutionField><ExecutionField label="DLQ event ID" mono>{event.id}</ExecutionField><ExecutionField label="Step attempts">{event.attempts}</ExecutionField><ExecutionField label="Event type">{event.event_type}</ExecutionField><ExecutionField label="Created">{formatTime(event.created_at)}</ExecutionField>{event.resolved_at && <ExecutionField label="Handled at">{formatTime(event.resolved_at)}</ExecutionField>}</dl></section>
          <section className="dlq-inspector-section" aria-label="Related execution attempts"><button type="button" className="dlq-attempts-toggle" aria-expanded={showAttempts} aria-controls="dlq-attempt-history" onClick={() => setShowAttempts(value => !value)}><span><ExecutionIcon type="history"/>Original run & replays</span><span aria-hidden="true">{showAttempts ? "−" : "+"}</span></button><p className="dlq-description mt-2">Follow the original failure and every replay in one place.</p>{showAttempts && <div id="dlq-attempt-history" className="mt-4"><ExecutionAttemptHistory key={historyRevision} executionId={event.execution_id}/></div>}</section>
          <p className="dlq-time-note"><ExecutionIcon type="clock"/>Times shown in your local timezone</p>
        </>}
      </div>
      {event && error?.status !== 404 && <footer className="dlq-drawer-footer"><div><h3>{event.status === "pending" ? (replayRejected ? "Resolve this event" : "Choose a recovery action") : "Event handled"}</h3><p>{needsRefresh ? "Refresh to confirm the current status before taking action." : event.status === "pending" ? (replayRejected ? "Mark resolved closes the event without running the workflow again." : "Replay starts a new attempt from the failed step.") : "Replay and resolve are unavailable for handled events."}</p></div><div className="dlq-action-buttons"><button disabled={disabled || replayRejected} onClick={() => { setActionError(null); setAction("replay"); }} className={`${executionAction} ${replayRejected ? "" : "is-primary"}`}><ExecutionIcon type="replay"/>{replayRejected ? "Replay unavailable" : "Replay execution"}</button><button ref={resolveButton} disabled={disabled} onClick={() => { setActionError(null); setAction("resolve"); }} className={`${executionAction} ${replayRejected ? "is-primary" : "is-resolve"}`}><ExecutionIcon type="check"/>Mark resolved</button></div></footer>}
    </div>
    {action && <DeadLetterConfirmation action={action} busy={processing} error={actionError} onClose={() => setAction(null)} onConfirm={confirm}/>}
  </dialog>;
}
