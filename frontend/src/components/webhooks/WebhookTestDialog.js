"use client";

import { useEffect, useRef, useState } from "react";
import { getWebhookTestEndpoint, getWebhookTestSession, startWebhookTestSession } from "@/services/webhooks";

const TEST_TIMEOUT_SECONDS = 120;

function errorText(status, detail) {
  if (status === 401) return "Invalid webhook secret. Check the X-Relay-Secret header in Postman.";
  if (status === 403) return "Webhook is inactive. Enable it, then start a new test.";
  if (status === 404) return "Webhook not found. The endpoint may have been regenerated or deleted.";
  if (status === 400) return "The request body must contain valid JSON.";
  return detail || "The test request failed. Check the endpoint and try again.";
}

export default function WebhookTestDialog({ open, webhook, onClose }) {
  const [copied, setCopied] = useState("");
  const [stage, setStage] = useState("starting");
  const [sessionId, setSessionId] = useState("");
  const [remaining, setRemaining] = useState(TEST_TIMEOUT_SECONDS);
  const [result, setResult] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const isOpen = Boolean(open && webhook);
  const baseEndpoint = isOpen ? getWebhookTestEndpoint(webhook.public_token) : "";
  const endpoint = baseEndpoint && sessionId ? `${baseEndpoint}?relay_test_session=${encodeURIComponent(sessionId)}` : baseEndpoint;
  const needsSecret = webhook?.authentication_type !== "none";

  useEffect(() => {
    if (!isOpen || !webhook?.id) return undefined;
    const run = ++generation.current;
    let cancelled = false;
    const active = () => !cancelled && generation.current === run;
    setCopied(""); setStage("starting"); setSessionId(""); setRemaining(TEST_TIMEOUT_SECONDS); setResult(null); setError("");

    const watch = async () => {
      try {
        const created = await startWebhookTestSession(webhook.id);
        if (!active()) return;
        setSessionId(created.session_id);
        setStage("waiting");
        const deadline = Date.now() + Math.min(created.timeout_seconds || TEST_TIMEOUT_SECONDS, TEST_TIMEOUT_SECONDS) * 1000;
        while (active() && Date.now() < deadline) {
          const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
          setRemaining(seconds);
          try {
            const session = await getWebhookTestSession(webhook.id, created.session_id);
            if (!active()) return;
            if (session.status === "success" && session.result?.received === true) { setResult(session.result); setStage("success"); return; }
            if (session.status === "failed") { setResult(session.result); setError(errorText(session.result?.status_code, session.result?.detail)); setStage("failed"); return; }
          } catch (pollError) {
            // A missing session can happen during startup (or after an app restart).
            // It is not a webhook failure; keep listening until the visible timeout.
          }
          await new Promise((resolve) => window.setTimeout(resolve, 1200));
        }
        if (active()) { setRemaining(0); setStage("timeout"); }
      } catch (err) {
        if (active()) {
          const message = err?.message || "Unable to start the test session.";
          setError(message === "Not Found"
            ? "Relay could not find the test-session API. Restart the API Gateway and Integration Service so they load the webhook test-session routes."
            : `Could not prepare the test environment: ${message}`);
          setStage("setup-error");
        }
      }
    };
    watch();
    return () => { cancelled = true; generation.current += 1; };
  }, [isOpen, webhook?.id, attempt]);

  if (!isOpen) return null;
  const copy = async (value, label) => {
    try { await navigator.clipboard.writeText(value); setCopied(label); setError(""); window.setTimeout(() => setCopied(""), 1800); }
    catch { setError("Unable to copy. Select and copy the value manually."); }
  };
  const status = {
    starting: { title: "Preparing test environment", detail: "Opening a secure, temporary result channel…", tone: "neutral" },
    waiting: { title: "Waiting for your request", detail: `Send this URL from Postman or your system · ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")} remaining`, tone: "waiting" },
    success: { title: "Webhook test passed", detail: "Relay received the request and captured its payload.", tone: "success" },
    failed: { title: "Webhook test failed", detail: error, tone: "failure" },
    "setup-error": { title: "Test environment unavailable", detail: error, tone: "neutral" },
    timeout: { title: "Test timed out", detail: "No matching request arrived. Start another test to try again.", tone: "failure" },
  }[stage];
  const tone = status.tone === "success"
    ? { frame: "border-emerald-500/35 bg-emerald-500/[0.06]", icon: "border-emerald-500/30 bg-emerald-500/10 text-emerald-500", dot: "bg-emerald-500", label: "Verified" }
    : status.tone === "failure"
      ? { frame: "border-red-500/35 bg-red-500/[0.05]", icon: "border-red-500/30 bg-red-500/10 text-red-500", dot: "bg-red-500", label: stage === "timeout" ? "Timed out" : "Failed" }
      : { frame: "border-[var(--border-default)] bg-[var(--elevated)]", icon: "border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-secondary)]", dot: "bg-[var(--accent)]", label: stage === "starting" ? "Preparing" : stage === "setup-error" ? "Unavailable" : "Listening" };

  return <div className="fixed inset-0 z-[115] flex justify-end bg-black/60 backdrop-blur-[2px]">
    <aside role="dialog" aria-modal="true" aria-labelledby="webhook-test-title" className="flex h-full w-full max-w-[500px] flex-col border-l border-[var(--border-default)] bg-[var(--surface)] shadow-2xl animate-in slide-in-from-right duration-300">
      <header className="border-b border-[var(--border-subtle)] px-5 py-4"><div className="flex items-start justify-between gap-4"><div className="flex items-start gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-[7px] border border-[var(--border-default)] bg-[var(--elevated)] font-mono text-[15px] text-[var(--accent)]" aria-hidden="true">↗</span><div><p className="font-mono text-[9px] uppercase tracking-[.16em] text-[var(--text-tertiary)]">Webhook / Diagnostics</p><h2 id="webhook-test-title" className="mt-1 text-[17px] font-semibold tracking-tight text-[var(--text-primary)]">Test environment</h2><p className="mt-1 text-[11px] leading-4 text-[var(--text-secondary)]">{webhook.name || "Webhook"}<span className="mx-1.5 text-[var(--text-disabled)]">·</span><span className="font-mono">{webhook.method || "POST"}</span></p></div></div><button type="button" aria-label="Close test environment" onClick={onClose} className="grid h-8 w-8 shrink-0 place-items-center rounded-[6px] border border-[var(--border-subtle)] text-[16px] text-[var(--text-tertiary)] transition hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]">×</button></div></header>
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        <section role="status" aria-live="polite" className={`relative overflow-hidden rounded-[8px] border p-4 transition-all duration-300 ${tone.frame} ${stage === "success" ? "animate-in zoom-in-95" : stage === "failed" || stage === "timeout" ? "animate-in fade-in" : ""}`}>
          {(stage === "waiting" || stage === "starting") && <div className="absolute inset-x-0 top-0 h-px overflow-hidden bg-[var(--border-subtle)]"><span className="block h-full w-1/3 animate-pulse bg-[var(--accent)]"/></div>}
          <div className="flex items-start gap-3"><span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full border text-[14px] font-semibold ${tone.icon} ${stage === "success" ? "animate-in zoom-in duration-300" : ""}`}>{stage === "success" ? "✓" : stage === "failed" || stage === "timeout" ? "!" : stage === "starting" ? "…" : <span className="relative flex h-2 w-2"><span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-40 ${tone.dot}`}/><span className={`relative inline-flex h-2 w-2 rounded-full ${tone.dot}`}/></span>}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="text-[12px] font-semibold text-[var(--text-primary)]">{status.title}</h3><span className="rounded-full border border-[var(--border-subtle)] px-2 py-0.5 font-mono text-[8px] uppercase tracking-wide text-[var(--text-tertiary)]">{tone.label}</span></div><p className="mt-1.5 text-[10px] leading-[17px] text-[var(--text-secondary)]">{status.detail}</p></div>{stage === "waiting" && <div className="shrink-0 text-right"><p className="font-mono text-[15px] font-medium tabular-nums text-[var(--text-primary)]">{String(Math.floor(remaining / 60)).padStart(2, "0")}:{String(remaining % 60).padStart(2, "0")}</p><p className="text-[8px] uppercase tracking-wide text-[var(--text-tertiary)]">remaining</p></div>}</div>
          {stage === "waiting" && <div className="mt-4 h-1 overflow-hidden rounded-full bg-[var(--surface)]"><div className="h-full rounded-full bg-[var(--accent)] transition-[width] duration-1000" style={{ width: `${Math.max(0, Math.min(100, (remaining / TEST_TIMEOUT_SECONDS) * 100))}%` }}/></div>}
        </section>
        {!webhook.is_active && stage !== "success" && <div className="flex items-start gap-2 rounded-[6px] border border-amber-500/30 bg-amber-500/5 p-3"><span className="font-semibold text-amber-600 dark:text-amber-400">!</span><p className="text-[10px] leading-4 text-[var(--text-secondary)]">This webhook is inactive. Enable it before sending a test request.</p></div>}
        {attempt > 0 && stage === "waiting" && <div role="status" className="flex items-start gap-2 rounded-[6px] border border-cyan-500/30 bg-cyan-500/[0.06] p-3 animate-in fade-in slide-in-from-top-1 duration-200"><span className="font-semibold text-cyan-500">↻</span><p className="text-[10px] leading-4 text-[var(--text-secondary)]"><span className="font-semibold text-[var(--text-primary)]">New test URL generated.</span> Replace the previous URL in Postman or your system with the one below before sending another request.</p></div>}
        <section className="rounded-[7px] border border-[var(--border-subtle)]"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2.5"><div className="flex items-center gap-2"><span className="font-mono text-[9px] text-[var(--text-tertiary)]">01</span><h3 className="text-[10px] font-semibold text-[var(--text-primary)]">Send a request</h3></div><span className="rounded border border-[var(--border-subtle)] bg-[var(--elevated)] px-1.5 py-0.5 font-mono text-[8px] text-[var(--text-secondary)]">POST</span></div><div className="p-3"><p className="mb-2 text-[9px] leading-4 text-[var(--text-tertiary)]">Copy this session URL into Postman or your system. The test window listens for a matching request.</p><div className="rounded-[5px] border border-[var(--border-default)] bg-[var(--input-bg)] p-2.5"><code className="block max-h-16 overflow-y-auto break-all font-mono text-[10px] leading-[17px] text-[var(--text-primary)]">{endpoint}</code></div><button type="button" disabled={!sessionId} onClick={() => copy(endpoint, "endpoint")} className="mt-2.5 inline-flex h-8 items-center gap-2 rounded-[5px] bg-[var(--text-primary)] px-3 text-[10px] font-semibold text-[var(--canvas)] transition hover:opacity-90 disabled:cursor-wait disabled:opacity-45"><span aria-hidden="true">{copied === "endpoint" ? "✓" : "▢"}</span>{copied === "endpoint" ? "Endpoint copied" : attempt > 0 ? "Copy new test URL" : "Copy test endpoint"}</button></div></section>
        {stage === "success" && result?.received && <section className="overflow-hidden rounded-[7px] border border-emerald-500/30 animate-in slide-in-from-bottom-2 duration-300"><div className="flex items-center justify-between border-b border-emerald-500/20 bg-emerald-500/[0.05] px-3 py-2.5"><div className="flex items-center gap-2"><span className="grid h-5 w-5 place-items-center rounded-full bg-emerald-500/15 text-[10px] text-emerald-600 dark:text-emerald-400">✓</span><div><h3 className="text-[10px] font-semibold text-[var(--text-primary)]">Payload received</h3><p className="font-mono text-[8px] text-[var(--text-tertiary)]">{result.webhook_id || "Webhook"}</p></div></div><button type="button" onClick={() => copy(JSON.stringify(result.payload, null, 2), "payload")} className="h-7 rounded-[5px] border border-[var(--border-default)] bg-[var(--surface)] px-2 text-[9px] font-medium text-[var(--text-secondary)] transition hover:bg-[var(--elevated)]">{copied === "payload" ? "Copied" : "Copy JSON"}</button></div><pre className="max-h-64 overflow-auto bg-[var(--input-bg)] p-3 font-mono text-[10px] leading-[17px] text-[var(--text-primary)]">{JSON.stringify(result.payload, null, 2)}</pre></section>}
        <section className="rounded-[7px] border border-[var(--border-subtle)]"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2.5"><div className="flex items-center gap-2"><span className="font-mono text-[9px] text-[var(--text-tertiary)]">02</span><h3 className="text-[10px] font-semibold text-[var(--text-primary)]">Authentication</h3></div><span className={`rounded-full border px-2 py-0.5 font-mono text-[8px] uppercase tracking-wide ${needsSecret ? "border-[var(--border-subtle)] text-[var(--text-tertiary)]" : "border-emerald-500/30 text-emerald-600 dark:text-emerald-400"}`}>{needsSecret ? "Required" : "Open"}</span></div>{needsSecret ? <div className="p-3"><div className="flex items-center justify-between gap-2 rounded-[5px] border border-[var(--border-subtle)] bg-[var(--elevated)] px-2.5 py-2"><code className="truncate font-mono text-[10px] text-[var(--text-secondary)]">X-Relay-Secret: <span className="tracking-[.16em]">••••••••••••</span></code><button type="button" onClick={() => copy("X-Relay-Secret", "header")} className="shrink-0 rounded border border-[var(--border-default)] px-2 py-1 text-[8px] text-[var(--text-secondary)] transition hover:bg-[var(--surface)]">{copied === "header" ? "Copied" : "Copy name"}</button></div><p className="mt-2 text-[9px] leading-4 text-[var(--text-tertiary)]">Add the secret you saved at creation as the value for this header.</p></div> : <p className="p-3 text-[9px] leading-4 text-[var(--text-tertiary)]">This endpoint does not require a shared secret.</p>}</section>
        <div className="flex items-center gap-2 px-1 text-[9px] text-[var(--text-tertiary)]"><span className={`h-1.5 w-1.5 rounded-full ${stage === "success" ? "bg-emerald-500" : stage === "failed" || stage === "timeout" ? "bg-red-500" : "bg-[var(--text-disabled)]"}`}/><span>{stage === "success" ? "Request verified · payload captured" : stage === "failed" ? "Request rejected · review the message above" : stage === "timeout" ? "Listener closed · no request received" : "This listener closes automatically when the timer ends"}</span></div>
        {(stage === "failed" || stage === "timeout" || stage === "setup-error") && <div><button type="button" onClick={() => setAttempt((value) => value + 1)} className="h-8 w-full rounded-[5px] border border-[var(--border-default)] text-[10px] font-medium text-[var(--text-secondary)] transition hover:bg-[var(--elevated)]">{stage === "failed" ? "Retry test with new URL" : stage === "timeout" ? "Start another test" : "Retry setup"}</button>{stage === "failed" && <p className="mt-1.5 text-center text-[9px] leading-4 text-[var(--text-tertiary)]">A retry creates a new session URL. Copy it into your system before sending again.</p>}</div>}
      </div>
      <footer className="flex items-center justify-between border-t border-[var(--border-subtle)] p-4"><p className="text-[9px] text-[var(--text-tertiary)]">Close this panel at any time</p><button type="button" onClick={onClose} className="h-8 rounded-[5px] border border-[var(--border-default)] px-3 text-[10px] font-medium text-[var(--text-secondary)] transition hover:bg-[var(--elevated)]">Close</button></footer>
    </aside>
  </div>;
}
