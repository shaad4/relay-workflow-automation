"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { getWorkflowNodes, getWorkflowVersions, runWorkflow } from "@/services/workflows";
import { hasManualTrigger, loadManualTrigger, validateManualInput, manualRunError } from "./manualTrigger";

export default function RunWorkflowButton({ workflowId, workflowName, workflowStatus, publishedVersionId, versions, draftNodes, onRunRequested, iconOnly = false }) {
  const [triggerInfo, setTriggerInfo] = useState(null);
  const hasLocalDraft = !publishedVersionId && Array.isArray(draftNodes);
  useEffect(() => {
    if (hasLocalDraft) return;
    let active = true;
    loadManualTrigger({ workflowId, publishedVersionId, versions }, { getWorkflowNodes, getWorkflowVersions })
      .then((result) => { if (active) setTriggerInfo({ workflowId, publishedVersionId, versions, ...result }); })
      .catch(() => { if (active) setTriggerInfo(null); });
    return () => { active = false; };
  }, [workflowId, publishedVersionId, versions, hasLocalDraft]);
  const info = triggerInfo?.workflowId === workflowId && triggerInfo?.publishedVersionId === publishedVersionId && triggerInfo?.versions === versions ? triggerInfo : null;
  const isManual = hasLocalDraft ? hasManualTrigger(draftNodes) : info?.hasManualTrigger === true;
  const publishedNumber = info?.versionNumber;
  const isActive = ["active", "published"].includes(String(workflowStatus).toLowerCase());
  const canRun = isManual && isActive && Boolean(publishedVersionId);
  const [runOpen, setRunOpen] = useState(false);
  const [runInput, setRunInput] = useState("{}");
  const [runError, setRunError] = useState("");
  const [runPending, setRunPending] = useState(false);
  const [runResult, setRunResult] = useState(null);
  const runInputRef = useRef(null);
  const runPendingRef = useRef(false);
  const inputValidation = validateManualInput(runInput);
  const inputBytes = inputValidation.bytes ?? new TextEncoder().encode(runInput).length + 10;

  const formatRunInput = () => {
    if (inputValidation.error) { setRunError(inputValidation.error); return; }
    setRunInput(JSON.stringify(inputValidation.input, null, 2));
    setRunError("");
    runInputRef.current?.focus();
  };

  const handleRunInputKeyDown = (event) => {
    if (event.key !== "Tab") return;
    event.preventDefault();
    const field = event.currentTarget;
    const start = field.selectionStart;
    const end = field.selectionEnd;
    const updated = `${runInput.slice(0, start)}  ${runInput.slice(end)}`;
    setRunInput(updated);
    setRunError("");
    requestAnimationFrame(() => { field.selectionStart = field.selectionEnd = start + 2; });
  };

  useEffect(() => {
    if (!runOpen) return;
    const onEscape = (event) => { if (event.key === "Escape" && !runPending) setRunOpen(false); };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [runOpen, runPending]);

  const submitRun = async (event) => {
    event.preventDefault();
    if (!canRun || runPendingRef.current) return;
    const validation = validateManualInput(runInput);
    if (validation.error) { setRunError(validation.error); return; }
    runPendingRef.current = true;
    setRunPending(true);
    setRunError("");
    try {
      const result = await runWorkflow(workflowId, validation.input);
      setRunResult(result);
      if (onRunRequested) { onRunRequested({ ...result, requestedAt: Date.now() }); setRunOpen(false); }
    } catch (error) {
      setRunError(manualRunError(error));
    } finally { runPendingRef.current = false; setRunPending(false); }
  };


  if (!isManual) return null;
  return <>
    <button type="button" disabled={!canRun} aria-label={`Run ${workflowName}`} title={!publishedVersionId ? "Publish this workflow to run it" : !isActive ? "Activate this workflow to run it" : "Run Workflow"}
      onKeyDown={(event) => event.stopPropagation()}
      onClick={(event) => { event.stopPropagation(); setRunInput("{}"); setRunError(""); setRunResult(null); setRunOpen(true); }}
      className={iconOnly ? "flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-white shadow-sm transition-all hover:brightness-110 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)] disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100" : "h-8 px-3 rounded-[6px] bg-[var(--accent)] text-white text-[12px] font-medium flex items-center gap-1.5 hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"}>
      <svg viewBox="0 0 24 24" fill={iconOnly ? "currentColor" : "none"} stroke="currentColor" className={iconOnly ? "h-4 w-4 translate-x-px stroke-[1.5]" : "h-3.5 w-3.5 stroke-[1.8]"} aria-hidden="true"><path d="m8 5 11 7-11 7V5Z" /></svg>
      {!iconOnly && "Run Workflow"}
    </button>
      {runOpen && createPortal(
        <div onClick={(event) => event.stopPropagation()} onKeyDown={(event) => { event.stopPropagation(); if (event.key === "Escape" && !runPending) setRunOpen(false); }} className="fixed inset-0 z-[150] flex items-center justify-center bg-black/70 p-3 sm:p-6">
          <section role="dialog" aria-modal="true" aria-labelledby="manual-run-title" className="flex max-h-[min(90vh,760px)] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-primary)] shadow-2xl">
            <header className="flex items-start justify-between gap-4 border-b border-[var(--border-subtle)] px-5 py-4">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--accent)]">Manual trigger</p>
                <h2 id="manual-run-title" className="mt-1 text-lg font-semibold">{runResult ? "Workflow run requested" : "Run Workflow"}</h2>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">{runResult ? "Your workflow has been queued for execution." : "Start a new execution using the published version."}</p>
              </div>
              <button type="button" disabled={runPending} onClick={() => setRunOpen(false)} aria-label="Close Run Workflow dialog" className="rounded-md px-2 py-1 text-lg text-[var(--text-tertiary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] disabled:opacity-50">×</button>
            </header>
            {runResult ? (
              <div className="space-y-4 p-5 text-sm text-[var(--text-secondary)]">
                {runResult.event_id && <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--elevated)] p-3"><span className="block text-xs text-[var(--text-tertiary)]">Event ID</span><code className="mt-1 block break-all text-xs">{runResult.event_id}</code></div>}
                <div className="flex justify-end"><button type="button" onClick={() => setRunOpen(false)} className="rounded-md bg-[var(--accent)] px-4 py-2 text-white">Done</button></div>
              </div>
            ) : (
              <form onSubmit={submitRun} className="flex min-h-0 flex-col">
                <div className="space-y-4 overflow-y-auto p-5">
                  <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--elevated)] px-3 py-2 text-xs"><p className="font-medium">{workflowName}</p><p className="mt-1 text-[var(--text-tertiary)]">{publishedNumber != null ? `Published version ${publishedNumber}` : "Published version selected by the server"} · Manual Trigger</p></div>
                  <div>
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2"><label htmlFor="manual-run-input" className="text-xs font-medium">Trigger Input <span className="text-[var(--text-tertiary)]">(JSON object)</span></label><div className="flex gap-2"><button type="button" disabled={runPending || Boolean(inputValidation.error)} onClick={formatRunInput} className="rounded-md border border-[var(--border-default)] px-2.5 py-1 text-[11px] text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-40">Format JSON</button><button type="button" disabled={runPending} onClick={() => { setRunInput("{}"); setRunError(""); runInputRef.current?.focus(); }} className="rounded-md border border-[var(--border-default)] px-2.5 py-1 text-[11px] text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-40">Reset</button></div></div>
                    <div className="overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--input-bg)] focus-within:border-[var(--accent)] focus-within:ring-1 focus-within:ring-[var(--accent)]/30"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-1.5 font-mono text-[10px] text-[var(--text-tertiary)]"><span>JSON</span><span>Tab inserts spaces</span></div><textarea id="manual-run-input" ref={runInputRef} value={runInput} onChange={(event) => { setRunInput(event.target.value); setRunError(""); }} onKeyDown={handleRunInputKeyDown} disabled={runPending} rows={12} spellCheck={false} autoCapitalize="off" autoComplete="off" aria-invalid={Boolean(inputValidation.error || runError)} aria-describedby="manual-run-help manual-run-status" placeholder={'{\n  "order_id": "ORD-10027"\n}'} className="block min-h-52 max-h-[42vh] w-full resize-y bg-transparent p-3 font-mono text-[13px] leading-5 text-[var(--text-primary)] outline-none disabled:opacity-60" /></div>
                    <div id="manual-run-status" className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px]"><span className={inputValidation.error ? "text-amber-400" : "text-emerald-400"}>{inputValidation.error || "Valid JSON object"}</span><span className={inputBytes > 65536 ? "font-mono text-red-400" : "font-mono text-[var(--text-tertiary)]"}>{inputBytes.toLocaleString()} / 65,536 bytes</span></div>
                    <p id="manual-run-help" className="mt-2 text-[11px] text-[var(--text-tertiary)]">Fields become available as <code className="font-mono">{"{{trigger.data.field_name}}"}</code>.</p>
                  </div>
                  {runError && <p role="alert" className="rounded-md border border-red-500/30 bg-red-500/5 p-2 text-xs text-red-400">{runError}</p>}
                </div>
                <footer className="flex justify-end gap-2 border-t border-[var(--border-subtle)] px-5 py-4"><button type="button" disabled={runPending} onClick={() => setRunOpen(false)} className="rounded-md border border-[var(--border-default)] px-4 py-2 text-xs disabled:opacity-50">Cancel</button><button type="submit" disabled={!canRun || runPending || Boolean(inputValidation.error)} className="rounded-md bg-[var(--accent)] px-4 py-2 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-40">{runPending ? "Requesting…" : "Run Workflow"}</button></footer>
              </form>
            )}
          </section>
        </div>, document.body)}
  </>;
}
