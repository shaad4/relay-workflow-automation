"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getExecutions, getExecutionDetails, getExecutionSteps } from "@/services/executions";
import { executionError, formatDuration, formatTime, normalizeStatus, pollingDelay, latestCanvasRun, canvasExecutionState } from "@/lib/executions";
import { ExecutionIcon, ExecutionStatusBadge } from "@/components/dashboard/ExecutionUI";

export default function WorkflowExecutionPanel({ workflowId, versionId, runRequest, onSnapshot, onFocusNode, nodes, onViewRunVersion, canViewRunVersion }) {
  const [expanded, setExpanded] = useState(Boolean(runRequest));
  const [runs, setRuns] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [discoveryBusy, setDiscoveryBusy] = useState(false);
  const [discoveryError, setDiscoveryError] = useState("");
  const [following, setFollowing] = useState(true);
  const [focusedStep, setFocusedStep] = useState(null);
  const [followCanvas, setFollowCanvas] = useState(false);
  const refreshRef = useRef(null);
  const discoverRef = useRef(null);
  const scrollRef = useRef(null);
  const [watchLatest, setWatchLatest] = useState(true);

  useEffect(() => {
    let disposed = false;
    let inFlight = false;
    let timer;
    let controller;
    async function discover() {
      if (disposed || inFlight) return;
      clearTimeout(timer);
      if (document.hidden) { timer = setTimeout(discover, 5000); return; }
      inFlight = true; setDiscoveryBusy(true);
      controller = new AbortController();
      try {
        const response = await getExecutions({ pageSize: 100, signal: controller.signal });
        if (disposed) return;
        const matches = response.items.filter(run => run.workflow_id === workflowId);
        setRuns(matches); setDiscoveryError("");
        if (watchLatest) {
          const latest = latestCanvasRun(matches, workflowId, versionId);
          if (latest) setSelectedId(latest.id);
        }
      } catch (cause) { if (!disposed) setDiscoveryError(executionError(cause)); }
      finally { inFlight = false; if (!disposed) { setDiscoveryBusy(false); timer = setTimeout(discover, 5000); } }
    }
    discoverRef.current = discover;
    discover();
    return () => { disposed = true; clearTimeout(timer); controller?.abort(); discoverRef.current = null; };
  }, [workflowId, versionId, watchLatest]);

  useEffect(() => {
    if (!selectedId) return;
    let disposed = false;
    let inFlight = false;
    let timer;
    let controller;
    let lastStatus;
    async function refresh() {
      if (disposed || inFlight) return;
      clearTimeout(timer); inFlight = true; setBusy(true);
      controller = new AbortController();
      let delay = null;
      try {
        const results = await Promise.allSettled([
          getExecutionDetails(selectedId, { signal: controller.signal }),
          getExecutionSteps(selectedId, { signal: controller.signal }),
        ]);
        if (disposed) return;
        const failed = results.find(result => result.status === "rejected");
        if (failed) throw failed.reason;
        const execution = results[0].value;
        if (execution.workflow_id !== workflowId) throw new Error("Workflow mismatch");
        const next = { execution, steps: results[1].value.items };
        lastStatus = execution.status;
        setSnapshot(next); onSnapshot(next); setError("");
        delay = pollingDelay(execution.status);
      } catch (cause) {
        if (!disposed) {
          setError(executionError(cause));
          if (![401, 403, 404].includes(cause.status)) delay = pollingDelay(lastStatus);
        }
      } finally {
        inFlight = false;
        if (!disposed) { setBusy(false); if (delay !== null) timer = setTimeout(refresh, delay); }
      }
    }
    refreshRef.current = refresh;
    refresh();
    return () => { disposed = true; clearTimeout(timer); controller?.abort(); refreshRef.current = null; };
  }, [selectedId, workflowId, onSnapshot]);

  const current = snapshot?.execution.id === selectedId ? snapshot : null;
  const steps = current?.steps || [];
  const completed = steps.filter(step => normalizeStatus(step.status) === "completed").length;
  const { matchingVersion, unmatched } = canvasExecutionState(nodes, current, versionId);
  const runningStep = matchingVersion && steps.find(step => normalizeStatus(step.status) === "running" && nodes.some(node => String(node.data?.nodeId ?? node.data?.node_id ?? node.id) === String(step.node_id)));
  const runningNodeId = current && pollingDelay(current.execution.status) === 4000 ? runningStep?.node_id : null;
  useEffect(() => {
    if (followCanvas && runningNodeId) onFocusNode(runningNodeId);
  }, [followCanvas, runningNodeId, selectedId, onFocusNode]);

  const activityKey = steps.map(step => `${step.id}:${step.status}`).join("|");
  useEffect(() => {
    if (!expanded || !following || !scrollRef.current) return;
    const container = scrollRef.current;
    const active = container.querySelector('[data-active="true"]');
    const top = active ? Math.max(0, active.offsetTop - container.offsetTop - container.clientHeight / 2) : container.scrollHeight;
    container.scrollTo({ top, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" });
  }, [activityKey, expanded, following]);

  function selectRun(id) {
    setFollowCanvas(false); setWatchLatest(false); setFocusedStep(null); setSelectedId(id); setSnapshot(null); setError(""); setFollowing(true); onSnapshot(null);
  }

  return <section className={`builder-execution-panel ${expanded ? "is-expanded" : ""}`} aria-label="Workflow execution monitor" onKeyDown={event => event.stopPropagation()}>
    <div className="builder-execution-bar" onClick={event => {
      if (!event.target.closest("button, a")) setExpanded(value => !value);
    }}>
      <div className="builder-execution-heading"><span className="builder-execution-heading-icon"><ExecutionIcon type="history"/></span><div><h2>Execution activity</h2><p>{current ? `${completed} of ${steps.length} recorded steps completed` : "Watching for workflow runs"}</p></div></div>
      {current && !matchingVersion && <button type="button" className="builder-execution-canvas-action" disabled={!canViewRunVersion} title={canViewRunVersion ? "Switch canvas to the version used by this run" : "Save your changes before switching versions"} onClick={() => onViewRunVersion(current.execution.workflow_version_id)}>Different version · View run version ↗</button>}
      {current && matchingVersion && unmatched.length > 0 && <span className="builder-execution-canvas-warning" role="status">{unmatched.length} recorded steps missing from canvas</span>}
      {(runningNodeId || followCanvas) && <button type="button" className="builder-execution-canvas-action" aria-pressed={followCanvas} title={followCanvas ? "Stop automatically following processing nodes" : "Focus the running node and automatically follow subsequent steps"} onClick={() => setFollowCanvas(value => !value)}>{followCanvas ? "Following canvas · Stop ⌖" : "Focus running step ⌖"}</button>}
      <div className="builder-execution-header-status">{current && <ExecutionStatusBadge status={current.execution.status}/>}</div>
      <button type="button" className="builder-execution-toggle" title={expanded ? "Collapse execution activity" : "Expand execution activity"} aria-label={expanded ? "Collapse execution activity" : "Expand execution activity"} aria-expanded={expanded} aria-controls="builder-execution-body" onClick={() => setExpanded(value => !value)}><svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" className="builder-execution-chevron" aria-hidden="true"><path d="m5 12 5-5 5 5"/></svg></button>
    </div>
    <div id="builder-execution-body" hidden={!expanded}>
      <div className="builder-execution-controls"><label className="builder-execution-run-label" htmlFor="builder-run-select">Run</label><select id="builder-run-select" value={selectedId} onChange={event => selectRun(event.target.value)}><option value="">Select a recent run</option>{selectedId && !runs.some(run => run.id === selectedId) && <option value={selectedId}>Run {selectedId.slice(0, 8)}</option>}{runs.map(run => <option key={run.id} value={run.id}>{run.id.slice(0, 8)} · {formatTime(run.started_at || run.created_at)} · {run.status}</option>)}</select><button type="button" aria-label="Refresh execution activity" title="Refresh runs and steps" disabled={busy || discoveryBusy} onClick={() => { discoverRef.current?.(); refreshRef.current?.(); }}><ExecutionIcon type="refresh" className={`h-3.5 w-3.5 ${busy || discoveryBusy ? "motion-safe:animate-spin" : ""}`}/><span>Refresh</span></button><button type="button" aria-pressed={following} onClick={() => setFollowing(value => !value)} disabled={!current} title="Automatically scroll to the active step. Scroll up to pause following." className={following && current ? "is-following" : ""}><span aria-hidden="true">{following ? "◉" : "◎"}</span>{following ? "Following" : "Follow live"}</button>{current && <Link className="builder-execution-link" href={`/dashboard/executions/${encodeURIComponent(selectedId)}`} target="_blank" rel="noopener noreferrer">Full run ↗</Link>}</div>
      <div className="builder-execution-watch"><label><input type="checkbox" checked={watchLatest} onChange={event => { setWatchLatest(event.target.checked); if (event.target.checked) { setSnapshot(null); onSnapshot(null); } }}/><span>Follow latest run</span></label><span>{watchLatest ? "New runs appear automatically, even with this panel collapsed" : "Viewing selected run"}</span></div>
      {runRequest && !current && <p className="builder-execution-notice">Run requested. Watching recent workflow runs; you can also select a run above.</p>}
      {current && !matchingVersion && <p className="builder-execution-notice">This run used a different version. <button type="button" disabled={!canViewRunVersion} onClick={() => onViewRunVersion(current.execution.workflow_version_id)} className="underline underline-offset-2 disabled:opacity-50">View run version</button>{!canViewRunVersion && " · Save your changes before switching."}</p>}
      {(error || discoveryError) && <p role="alert" className="builder-execution-notice is-error">{error || discoveryError} Use Refresh to try again.</p>}
      {current && <div className="builder-execution-run-summary"><span className="font-mono">#{selectedId.slice(0, 8)}</span><span>{formatDuration(current.execution.duration_ms)} total</span><span className="ml-auto">{matchingVersion ? "Select a step to focus its node" : "Viewing another version"}</span></div>}
      <div className="builder-execution-scroll" ref={scrollRef} onWheel={() => setFollowing(false)} onTouchMove={() => setFollowing(false)} onKeyDown={event => { if (["ArrowUp", "PageUp", "Home"].includes(event.key)) setFollowing(false); }} tabIndex={0} aria-label="Recorded execution steps">
        {busy && !current ? <div role="status" className="builder-execution-empty">Loading execution steps…</div> : steps.length ? <ol>{steps.map(step => {
          const canFocus = matchingVersion && nodes.some(node => String(node.data?.nodeId ?? node.data?.node_id ?? node.id) === String(step.node_id));
          return <li key={step.id} data-focused={focusedStep === step.id} data-active={normalizeStatus(step.status) === "running"}><button type="button" disabled={!canFocus} onClick={() => { setFollowCanvas(false); setFocusedStep(step.id); onFocusNode(step.node_id); }} title={canFocus ? "Focus this node on the canvas" : "Node is not available in the current canvas"}><span className="builder-execution-sequence">{String(step.sequence).padStart(2, "0")}</span><span className="builder-execution-node-icon"><ExecutionIcon type={step.node_type || "generic"}/></span><span className="builder-execution-step-name">{step.node_name || step.node_id}<small>{step.node_type || "Unknown node type"} · Attempt {step.attempt}</small></span><ExecutionStatusBadge status={step.status}/><span className="builder-execution-duration">{formatDuration(step.duration_ms)}</span></button></li>;
        })}</ol> : <div className="builder-execution-empty"><ExecutionIcon type="history" className="h-6 w-6"/><strong>{current ? "Waiting for recorded steps" : "Follow a workflow run"}</strong><span>{current ? "Step activity appears here as execution progresses." : "Select a recent run above to inspect its progress on the canvas."}</span></div>}
      </div>
      <div className="builder-execution-footer"><span role="status">{current ? error ? "Updates interrupted" : pollingDelay(current.execution.status) === 4000 ? "● Live · Updates every 4s" : pollingDelay(current.execution.status) === 30000 ? "Paused for approval · Updates every 30s" : "Auto-refresh off" : "Runs from the latest 100 workspace executions"}</span><Link href="/dashboard/executions" target="_blank" rel="noopener noreferrer">All history ↗</Link></div>
    </div>
  </section>;
}
