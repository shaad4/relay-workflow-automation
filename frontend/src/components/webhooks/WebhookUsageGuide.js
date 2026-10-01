"use client";

import { useEffect } from "react";
import { getWebhookEndpoint } from "@/services/webhooks";

const steps = [
  ["Create the endpoint", "Set an event name and choose whether requests need a shared secret. Keep the webhook active to accept calls."],
  ["Register the URL", "In the service that sends events, add this endpoint as a POST webhook URL. Use the test URL from the Test environment when validating."],
  ["Add authentication", "When Secret is enabled, send the X-Relay-Secret header with the secret shown once when the webhook was created."],
  ["Send JSON", "Send event data as a JSON request body. Relay validates the request and starts the workflow linked to this webhook."],
];

export default function WebhookUsageGuide({ open, onClose, webhook }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;
  const endpoint = webhook?.public_token ? getWebhookEndpoint(webhook.public_token) : "https://your-relay-host/hooks/{public_token}";
  const needsSecret = webhook?.authentication_type !== "none";
  const sample = [
    `curl -X POST '${endpoint}'`,
    "  -H 'Content-Type: application/json'",
    ...(needsSecret ? ["  -H 'X-Relay-Secret: YOUR_SAVED_SECRET'"] : []),
    `  -d '{\"event\": \"purchase.created\", \"order_id\": \"ORD-1001\"}'`,
  ].join(" \\\n");

  const copySample = async () => {
    try { await navigator.clipboard.writeText(sample); }
    catch { /* The code sample remains selectable for manual copying. */ }
  };

  return <div className="fixed inset-0 z-[130] flex items-center justify-center bg-black/60 p-4 backdrop-blur-[2px]" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <section role="dialog" aria-modal="true" aria-labelledby="webhook-guide-title" className="max-h-[90vh] w-full max-w-[560px] overflow-y-auto rounded-[9px] border border-[var(--border-default)] bg-[var(--surface)] shadow-2xl animate-in fade-in zoom-in-95 duration-150">
      <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[var(--border-subtle)] bg-[var(--surface)] px-5 py-4"><div className="flex items-start gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-[7px] border border-[var(--border-default)] bg-[var(--elevated)] font-mono text-[15px] text-cyan-500">?</span><div><p className="font-mono text-[9px] uppercase tracking-[.15em] text-[var(--text-tertiary)]">Webhook · Quick guide</p><h2 id="webhook-guide-title" className="mt-1 text-[16px] font-semibold tracking-tight text-[var(--text-primary)]">Connect your system</h2><p className="mt-1 text-[11px] leading-4 text-[var(--text-secondary)]">Another service can start this workflow by sending an event to Relay.</p></div></div><button type="button" aria-label="Close webhook guide" onClick={onClose} className="grid h-8 w-8 shrink-0 place-items-center rounded-[6px] border border-[var(--border-subtle)] text-[16px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)]">×</button></header>
      <div className="space-y-5 p-5">
        <ol className="space-y-0">{steps.map(([title, description], index) => <li key={title} className="relative flex gap-3 pb-4 last:pb-0">{index < steps.length - 1 && <span className="absolute bottom-0 left-[13px] top-7 w-px bg-[var(--border-subtle)]"/>}<span className="z-[1] grid h-[27px] w-[27px] shrink-0 place-items-center rounded-full border border-[var(--border-default)] bg-[var(--surface)] font-mono text-[10px] text-[var(--text-secondary)]">{String(index + 1).padStart(2, "0")}</span><div className="pt-0.5"><h3 className="text-[11px] font-semibold text-[var(--text-primary)]">{title}</h3><p className="mt-1 text-[10px] leading-[17px] text-[var(--text-secondary)]">{description}</p></div></li>)}</ol>
        <section><div className="mb-2 flex items-center justify-between"><div><h3 className="text-[10px] font-semibold text-[var(--text-primary)]">Example request</h3><p className="mt-0.5 text-[9px] text-[var(--text-tertiary)]">Use this as a template in Postman or your integration.</p></div><button type="button" onClick={copySample} className="h-7 rounded-[5px] border border-[var(--border-default)] px-2 text-[9px] font-medium text-[var(--text-secondary)] hover:bg-[var(--elevated)]">Copy example</button></div><pre className="overflow-x-auto rounded-[6px] border border-[var(--border-subtle)] bg-[var(--input-bg)] p-3 font-mono text-[9px] leading-[16px] text-[var(--text-secondary)]">{sample}</pre></section>
        <div className="rounded-[6px] border border-[var(--border-subtle)] bg-[var(--elevated)] p-3"><p className="text-[10px] font-medium text-[var(--text-primary)]">Testing tip</p><p className="mt-1 text-[9px] leading-4 text-[var(--text-tertiary)]">Open <span className="font-medium text-[var(--text-secondary)]">Test environment</span> to get a temporary test URL. Send your request before its timer expires; Relay will show the response payload there.</p></div>
      </div>
      <footer className="flex justify-end border-t border-[var(--border-subtle)] p-4"><button type="button" onClick={onClose} className="h-8 rounded-[5px] bg-[var(--text-primary)] px-4 text-[10px] font-semibold text-[var(--canvas)] hover:opacity-90">Got it</button></footer>
    </section>
  </div>;
}
