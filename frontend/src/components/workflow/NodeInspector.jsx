"use client";

import { useState, useEffect } from "react";
import { getNodeDefinition } from "./nodeDefinitions";
import { createWebhook, deleteWebhook, getWebhookEndpoint, listWebhooks, regenerateWebhookToken, updateWebhook } from "@/services/webhooks";
import { getWorkflowVersions } from "@/services/workflows";
import { listConnections } from "@/services/connections";
import Link from "next/link";
import WebhookTestDialog from "@/components/webhooks/WebhookTestDialog";
import WebhookUsageGuide from "@/components/webhooks/WebhookUsageGuide";

// ─────────────────────────────────────────────────────────────────────────────
// Icons
// ─────────────────────────────────────────────────────────────────────────────
function TrashIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function SaveIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
      <polyline points="17 21 17 13 7 13 7 21" />
      <polyline points="7 3 7 8 15 8" />
    </svg>
  );
}

function SettingsIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function XIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Config field components
// ─────────────────────────────────────────────────────────────────────────────
function FieldLabel({ children }) {
  return (
    <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1 uppercase tracking-wide">
      {children}
    </label>
  );
}

function TextInput({ value, onChange, placeholder, mono = false }) {
  return (
    <input
      type="text"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full h-8 px-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-colors ${mono ? "font-mono" : ""}`}
    />
  );
}

function TextareaInput({ value, onChange, placeholder, rows = 3, mono = false }) {
  return (
    <textarea
      rows={rows}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full p-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-colors resize-none ${mono ? "font-mono" : ""}`}
    />
  );
}

function SelectInput({ value, onChange, options }) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="w-full h-8 px-2 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:outline-none"
    >
      {options.map(({ value: v, label }) => (
        <option key={v} value={v}>{label}</option>
      ))}
    </select>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Per-node-type configuration panels
// ─────────────────────────────────────────────────────────────────────────────
function WebhookConfig({ config, workflowId, workflowVersionId, nodeId, isReadOnly, onAssociate, onOpenGuide }) {
  const [webhook, setWebhook] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState("");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [secretVisible, setSecretVisible] = useState(false);
  const [oneTimeSecret, setOneTimeSecret] = useState("");
  const [testOpen, setTestOpen] = useState(false);
  const [form, setForm] = useState({ name: "", event_name: "", authentication_type: "secret", is_active: true });

  const load = async () => {
    // The create response is the only source of plaintext credentials. A list
    // reload deliberately omits them, so don't replace the live creation
    // result while its one-time secret is being shown.
    if (dialog === "secret" && oneTimeSecret) return;
    if (!workflowId) { setLoading(false); setError("Workflow context is unavailable."); return; }
    setLoading(true); setError(""); setWebhook(null);
    try {
      const raw = await listWebhooks();
      const records = Array.isArray(raw) ? raw : raw?.webhooks || raw?.results || raw?.data || [];
      // A trigger is associated with one specific webhook resource. Do not
      // fall back to another webhook from the same workflow/version: copied
      // or stale node config must never inherit a different version's trigger.
      const forVersion = records.filter((item) =>
        String(item.workflow_id) === String(workflowId) &&
        String(item.workflow_version_id) === String(workflowVersionId)
      );
      const linked = forVersion.find((item) => String(item.id) === String(config.webhook_id));
      // Older nodes may not have persisted webhook_id even though their
      // version already owns a webhook. Associate automatically only when
      // there is exactly one candidate for this exact version; never guess
      // between multiple endpoints or cross into another version.
      const match = linked || (forVersion.length === 1 ? forVersion[0] : null);
      setWebhook(match);
      if (match && String(match.id) !== String(config.webhook_id)) onAssociate(match);
      else if (!match && config.webhook_id) onAssociate(null);
    } catch { setError("Unable to load webhook configuration."); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId, workflowVersionId, nodeId, config.webhook_id]);
  useEffect(() => {
    if (!dialog) return undefined;
    const onKeyDown = (event) => {
      if (event.key !== "Escape" || saving) return;
      if (dialog === "secret") {
        setOneTimeSecret("");
        setWebhook((current) => {
          if (!current) return current;
          const safe = { ...current };
          delete safe.secret;
          return safe;
        });
      }
      setDialog("");
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [dialog, saving]);
  const endpoint = webhook ? getWebhookEndpoint(webhook.public_token) : "";
  const copyEndpoint = async () => { try { await navigator.clipboard.writeText(endpoint); setCopied(true); setTimeout(() => setCopied(false), 1600); } catch { setError("Unable to copy endpoint. Select and copy it manually."); } };
  const openCreate = () => { setForm({ name: "Webhook", event_name: config.event_name || "", authentication_type: "secret", is_active: true }); setDialog("create"); setError(""); };
  const openEdit = () => { setForm({ name: webhook.name || "", event_name: webhook.event_name || "", authentication_type: webhook.authentication_type || "secret", is_active: Boolean(webhook.is_active) }); setDialog("edit"); setError(""); };
  const submit = async (event) => {
    event?.preventDefault();
    if (!form.name.trim()) { setError("Webhook name is required."); return; }
    if (!form.event_name.trim()) { setError("Event name is required."); return; }
    setSaving(true); setError("");
    try {
      if (dialog === "create") {
        const versionsResult = await getWorkflowVersions(workflowId);
        const versions = Array.isArray(versionsResult) ? versionsResult : versionsResult?.versions || versionsResult?.results || versionsResult?.data || [];
        const version = versions.find((item) => item.id === workflowVersionId);
        if (!version) throw new Error("The current workflow version is unavailable.");
        const created = await createWebhook({ workflow_id: workflowId, workflow_version_id: workflowVersionId, name: form.name.trim(), event_name: form.event_name.trim(), method: "POST", authentication_type: form.authentication_type, is_active: form.is_active });
        setWebhook(created); onAssociate(created); setOneTimeSecret(created.secret || ""); setSecretVisible(false); setCopied(false); setDialog(created.secret ? "secret" : "");
      } else {
        const patch = {};
        for (const key of ["name", "event_name", "authentication_type", "is_active"]) if (form[key] !== webhook[key]) patch[key] = form[key];
        const updated = Object.keys(patch).length ? await updateWebhook(webhook.id, patch) : webhook;
        setWebhook({ ...webhook, ...updated, ...patch }); setDialog("");
      }
    } catch (err) { setError(err.message || `Unable to ${dialog === "create" ? "create" : "update"} webhook. Please try again.`); }
    finally { setSaving(false); }
  };
  const setActive = async (active) => { setSaving(true); setError(""); try { await updateWebhook(webhook.id, { is_active: active }); setWebhook((value) => ({ ...value, is_active: active })); } catch { setError("Unable to update webhook. Please try again."); } finally { setSaving(false); } };
  const regenerate = async () => { setSaving(true); setError(""); try { const result = await regenerateWebhookToken(webhook.id); const token = result?.public_token || result?.webhook?.public_token || result?.data?.public_token; if (!token) throw new Error(); setWebhook((value) => ({ ...value, public_token: token })); setDialog(""); } catch { setError("Unable to regenerate the webhook URL. Please try again."); } finally { setSaving(false); } };
  const removeWebhook = async () => {
    if (!webhook) return;
    setSaving(true); setError("");
    try {
      await deleteWebhook(webhook.id);
      setWebhook(null);
      onAssociate(null);
      setDialog("");
    } catch { setError("Unable to delete the webhook. Please try again."); }
    finally { setSaving(false); }
  };
  const inputClass = "w-full h-8 px-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none";
  const closeDialog = () => {
    if (saving) return;
    if (dialog === "secret") {
      setOneTimeSecret("");
      setWebhook((current) => {
        if (!current) return current;
        const safe = { ...current };
        delete safe.secret;
        return safe;
      });
    }
    setDialog("");
  };

  if (loading) return <div className="space-y-3"><div className="h-3 w-36 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-16 animate-pulse rounded-[6px] border border-[var(--border-subtle)] bg-[var(--elevated)]"/><p className="text-[11px] text-[var(--text-tertiary)]">Loading webhook configuration…</p></div>;
  if (error && !webhook) return <div className="space-y-2"><p role="alert" className="text-[11px] text-red-500">{error}</p><button type="button" onClick={load} className="text-[11px] text-[var(--accent)]">Retry</button></div>;
  return <div className="space-y-3">
    {webhook ? <>
      <div className="rounded-[6px] border border-[var(--border-subtle)] bg-[var(--elevated)] p-3"><div className="flex items-start justify-between gap-2"><div className="min-w-0"><p className="truncate text-[12px] font-medium text-[var(--text-primary)]">{webhook.name}</p><p className="mt-1 truncate font-mono text-[10px] text-[var(--text-tertiary)]">{webhook.event_name}</p></div><span className="shrink-0 text-[10px] text-[var(--text-secondary)]"><i className={`mr-1 inline-block h-1.5 w-1.5 rounded-full ${webhook.is_active ? "bg-emerald-500" : "bg-[var(--text-tertiary)]"}`}/>{webhook.is_active ? "Active" : "Inactive"}</span></div><div className="mt-3 grid grid-cols-2 gap-2 border-t border-[var(--border-subtle)] pt-2 text-[10px]"><div><span className="text-[var(--text-tertiary)]">Method</span><span className="ml-2 font-mono text-[var(--text-secondary)]">{webhook.method || "POST"}</span></div><div><span className="text-[var(--text-tertiary)]">Auth</span><span className="ml-2 text-[var(--text-secondary)]">{webhook.authentication_type === "none" ? "None" : "Secret"}</span></div></div></div>
      <section><div className="mb-1 flex items-center justify-between"><FieldLabel>Endpoint</FieldLabel><span className="font-mono text-[9px] text-[var(--text-tertiary)]">POST</span></div><div className="rounded-[6px] border border-[var(--border-default)] bg-[var(--input-bg)] p-2.5"><code title="Endpoint is masked" className="block truncate font-mono text-[10px] leading-4 text-[var(--text-secondary)]">{`${endpoint.split("/hooks/")[0]}/hooks/••••••••${String(webhook.public_token || "").slice(-4)}`}</code><div className="mt-2 flex gap-2 border-t border-[var(--border-subtle)] pt-2"><button type="button" onClick={copyEndpoint} className="h-7 flex-1 rounded-[5px] border border-[var(--border-default)] px-2 text-[10px] text-[var(--text-secondary)] hover:bg-[var(--elevated)]">{copied ? "Copied" : "Copy URL"}</button>{!isReadOnly && <button type="button" disabled={saving} onClick={()=>setDialog("regenerate")} className="h-7 flex-1 rounded-[5px] border border-[var(--border-default)] px-2 text-[10px] text-[var(--text-secondary)] hover:bg-[var(--elevated)]">Regenerate URL</button>}</div></div></section>
      <section className="overflow-hidden rounded-[7px] border border-[var(--border-default)] bg-[var(--elevated)]"><div className="flex items-start gap-2.5 p-3"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-[5px] border border-[var(--border-default)] bg-[var(--surface)] font-mono text-[12px] text-cyan-500" aria-hidden="true">↗</span><div className="min-w-0"><div className="flex items-center gap-1.5"><p className="text-[11px] font-semibold text-[var(--text-primary)]">Test this endpoint</p><span className="rounded border border-[var(--border-subtle)] px-1 py-0.5 font-mono text-[8px] text-[var(--text-tertiary)]">LIVE</span></div><p className="mt-1 text-[10px] leading-4 text-[var(--text-tertiary)]">Send a request from Postman or your system and inspect the payload here.</p></div></div><div className="border-t border-[var(--border-subtle)] p-2.5"><button type="button" onClick={()=>setTestOpen(true)} className="group flex h-8 w-full items-center justify-between rounded-[5px] border border-cyan-400/40 bg-cyan-600 px-3 text-[10px] font-semibold text-white transition hover:border-cyan-300/60 hover:bg-cyan-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60"><span className="flex items-center gap-2"><span className="grid h-4 w-4 place-items-center rounded-full border border-white/50 text-[8px]">▶</span>Open test environment</span><span aria-hidden="true" className="transition-transform group-hover:translate-x-0.5">→</span></button></div></section>
      {!isReadOnly && <><button type="button" onClick={openEdit} className="h-8 w-full rounded-[6px] bg-[var(--accent)] px-3 text-[11px] font-medium text-white hover:bg-[var(--accent-hover)]">Edit webhook</button><div className="flex items-center justify-between gap-3 rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-2.5"><div><p className="text-[11px] font-medium text-[var(--text-primary)]">Endpoint status</p><p className="mt-0.5 text-[10px] text-[var(--text-secondary)]"><i className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${webhook.is_active ? "bg-emerald-500" : "bg-[var(--text-tertiary)]"}`}/>{webhook.is_active ? "Active and accepting requests" : "Inactive and not accepting requests"}</p></div><button type="button" role="switch" aria-checked={Boolean(webhook.is_active)} aria-label={`${webhook.is_active ? "Disable" : "Enable"} webhook`} disabled={saving} onClick={() => setActive(!webhook.is_active)} className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 disabled:cursor-wait disabled:opacity-60 ${webhook.is_active ? "border-emerald-600 bg-emerald-600" : "border-[var(--border-strong)] bg-[var(--elevated)]"}`}><span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${webhook.is_active ? "translate-x-[17px]" : "translate-x-[3px]"}`}/></button></div></>}
    </> : <div className="space-y-2"><div className="rounded-[6px] border border-[var(--border-subtle)] p-3"><div className="flex items-center justify-between gap-2"><p className="text-[12px] font-medium text-[var(--text-primary)]">{config.setup_required ? "Webhook setup required" : "No webhook configured"}</p>{config.setup_required && <span className="rounded border border-amber-500/30 bg-amber-500/5 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wide text-amber-600 dark:text-amber-400">Setup required</span>}</div><p className="mt-1 text-[10px] leading-4 text-[var(--text-tertiary)]">{config.setup_required ? "This workflow version needs its own endpoint. Configure a new webhook URL for this version; other versions stay unchanged." : "Create an endpoint to trigger this workflow from an external service."}</p></div>{!isReadOnly && <button type="button" onClick={openCreate} className="h-8 w-full rounded-[6px] bg-[var(--accent)] px-3 text-[11px] font-medium text-white hover:bg-[var(--accent-hover)]">＋ {config.setup_required ? "Set up webhook" : "Create webhook"}</button>}</div>}
    {error && webhook && <p role="alert" className="text-[10px] text-red-500">{error}</p>}
    {dialog && <div className="fixed inset-0 z-[110] flex justify-end bg-black/55"><section role="dialog" aria-modal="true" aria-labelledby="webhook-trigger-dialog-title" className="flex h-full w-full max-w-[480px] flex-col overflow-y-auto border-l border-[var(--border-default)] bg-[var(--surface)] shadow-2xl animate-in slide-in-from-right duration-200"><div className="sticky top-0 z-10 border-b border-[var(--border-subtle)] bg-[var(--surface)] px-5 py-4"><div className="flex items-start justify-between gap-4"><div><p className="text-[9px] font-mono uppercase tracking-[.16em] text-[var(--text-tertiary)]">Webhook trigger · {dialog === "create" ? "New endpoint" : dialog === "edit" ? "Endpoint settings" : dialog === "secret" ? "Credentials" : dialog === "delete" ? "Destructive action" : "Security"}</p><h3 id="webhook-trigger-dialog-title" className="mt-1.5 text-[17px] font-semibold tracking-tight text-[var(--text-primary)]">{dialog === "create" ? "Configure webhook" : dialog === "edit" ? "Edit webhook" : dialog === "secret" ? "Webhook created" : dialog === "delete" ? "Delete webhook?" : "Regenerate endpoint URL?"}</h3><p className="mt-1 text-[11px] leading-4 text-[var(--text-secondary)]">{dialog === "create" ? "Set the endpoint details and trigger destination." : dialog === "edit" ? "Update this workflow's webhook settings." : dialog === "secret" ? "Copy and store the secret before closing." : dialog === "delete" ? "This permanently removes the endpoint." : "This change immediately invalidates the current URL."}</p></div><div className="flex shrink-0 items-center gap-2">{(dialog === "create" || dialog === "edit") && <button type="button" onClick={onOpenGuide} className="inline-flex h-8 items-center gap-1.5 rounded-[6px] border border-[var(--border-default)] px-2.5 text-[10px] font-medium text-[var(--text-secondary)] transition hover:bg-[var(--elevated)]" aria-label="Open webhook usage guide"><span className="grid h-4 w-4 place-items-center rounded-full border border-current font-mono text-[9px]">?</span>Guide</button>}<button type="button" disabled={saving} onClick={closeDialog} aria-label="Close webhook configuration" className="grid h-8 w-8 shrink-0 place-items-center rounded-[6px] border border-[var(--border-subtle)] text-[16px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)]">×</button></div></div></div>
      {(dialog === "create" || dialog === "edit") && <div role="group" aria-label="Webhook configuration" onKeyDown={(event) => { if (event.key === "Enter" && event.target.tagName !== "BUTTON") { event.preventDefault(); submit(); } }} className="flex-1 space-y-5 p-5"><section className="space-y-3"><div className="border-b border-[var(--border-subtle)] pb-2 text-[9px] font-mono uppercase tracking-[.14em] text-[var(--text-tertiary)]">Endpoint identity</div><label className="block text-[10px] font-medium text-[var(--text-secondary)]">Webhook name<input required maxLength={255} value={form.name} onChange={(e)=>setForm({...form,name:e.target.value})} className={`${inputClass} mt-1`} placeholder="Order Created Webhook"/></label><label className="block text-[10px] font-medium text-[var(--text-secondary)]">Event name<input required maxLength={255} value={form.event_name} onChange={(e)=>setForm({...form,event_name:e.target.value})} className={`${inputClass} mt-1 font-mono`} placeholder="orders.created"/></label></section><section className="space-y-3"><div className="border-b border-[var(--border-subtle)] pb-2 text-[9px] font-mono uppercase tracking-[.14em] text-[var(--text-tertiary)]">Request security</div><label className="block text-[10px] font-medium text-[var(--text-secondary)]">Method<select value="POST" disabled className={`${inputClass} mt-1 opacity-70`}><option>POST</option></select></label><label className="block text-[10px] font-medium text-[var(--text-secondary)]">Authentication<select value={form.authentication_type} onChange={(e)=>setForm({...form,authentication_type:e.target.value})} className={`${inputClass} mt-1`}><option value="secret">Secret</option><option value="none">None</option></select></label><label className="flex items-center justify-between rounded-[6px] border border-[var(--border-subtle)] bg-[var(--elevated)] p-3 text-[11px] text-[var(--text-secondary)]"><span><span className="block font-medium text-[var(--text-primary)]">Active</span><span className="mt-0.5 block text-[10px] text-[var(--text-tertiary)]">{form.is_active ? "Endpoint will accept requests" : "Endpoint will be paused"}</span></span><button type="button" role="switch" aria-checked={Boolean(form.is_active)} aria-label="Webhook active" onClick={()=>setForm({...form,is_active:!form.is_active})} className={`relative inline-flex h-5 w-9 items-center rounded-full border transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 ${form.is_active ? "border-emerald-600 bg-emerald-600" : "border-[var(--border-strong)] bg-[var(--surface)]"}`}><span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${form.is_active ? "translate-x-[17px]" : "translate-x-[3px]"}`}/></button></label></section>{dialog === "edit" && <section className="border-t border-[var(--border-subtle)] pt-4"><p className="text-[10px] font-medium text-[var(--text-primary)]">Danger zone</p><p className="mt-1 text-[10px] leading-4 text-[var(--text-tertiary)]">Permanently remove this webhook and invalidate its endpoint.</p><button type="button" onClick={()=>{setError("");setDialog("delete");}} className="mt-2 h-8 rounded-[6px] border border-red-500/30 px-3 text-[10px] text-red-600 hover:bg-red-500/5 dark:text-red-400">Delete webhook</button></section>}{dialog === "create" && <div className="rounded-[6px] border border-[var(--border-subtle)] bg-[var(--elevated)] p-3 text-[10px] leading-4 text-[var(--text-secondary)]">{form.authentication_type === "secret" ? "Relay generates the secret automatically. It is displayed once after creation." : "Requests to this endpoint will not require a shared secret."}</div>}{error&&<p role="alert" className="rounded-[6px] border border-red-500/30 bg-red-500/5 p-2 text-[10px] text-red-500">{error}</p>}<div className="sticky bottom-0 -mx-5 mt-auto flex justify-end gap-2 border-t border-[var(--border-subtle)] bg-[var(--surface)] px-5 py-4"><button type="button" onClick={closeDialog} className="h-8 rounded-[6px] border border-[var(--border-default)] px-3 text-[11px] text-[var(--text-secondary)]">Cancel</button><button type="button" onClick={() => submit()} disabled={saving} className="h-8 rounded-[6px] bg-[var(--accent)] px-3 text-[11px] font-medium text-white">{saving ? (dialog === "create" ? "Creating…" : "Saving…") : (dialog === "create" ? "Create webhook" : "Save changes")}</button></div></div>}
      {dialog === "secret" && <div className="flex-1 space-y-5 p-5"><div className="rounded-[6px] border border-amber-500/30 bg-amber-500/5 p-4"><div className="flex items-start gap-3"><span aria-hidden="true" className="grid h-7 w-7 shrink-0 place-items-center rounded border border-amber-500/30 font-semibold text-amber-600 dark:text-amber-400">!</span><div><p className="text-[12px] font-semibold text-[var(--text-primary)]">Copy this secret now</p><p className="mt-1 text-[11px] leading-5 text-[var(--text-secondary)]">This is the only time Relay will show it. If you close this drawer without saving it, you’ll need to create a new webhook to get another secret.</p></div></div></div><section><div className="mb-2 flex items-center justify-between"><FieldLabel>Signing secret</FieldLabel><span className="font-mono text-[9px] uppercase tracking-wide text-[var(--text-tertiary)]">Sensitive</span></div><div className="rounded-[6px] border border-[var(--border-default)] bg-[var(--input-bg)] p-3"><code className="block min-h-5 break-all font-mono text-[12px] leading-5 text-[var(--text-primary)]" aria-label={secretVisible?"Signing secret":"Masked signing secret"}>{secretVisible ? oneTimeSecret : `${String(oneTimeSecret || "").slice(0, 10)}${"•".repeat(Math.max(12, String(oneTimeSecret || "").length - 10))}`}</code><div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={async()=>{if(!oneTimeSecret){setError("Relay did not return the signing secret. Create a new webhook to receive a new secret.");return;}try{await navigator.clipboard.writeText(oneTimeSecret);setCopied(true);setError("");}catch{setError("Unable to copy secret. Select and copy it manually.");}}} className={`h-8 rounded-[6px] px-3 text-[11px] font-medium ${copied?"border border-emerald-600/40 text-emerald-600 dark:text-emerald-400":"bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]"}`}>{copied?"✓ Copied":"Copy secret"}</button><button type="button" onClick={()=>setSecretVisible((value)=>!value)} aria-pressed={secretVisible} className="h-8 rounded-[6px] border border-[var(--border-default)] px-3 text-[11px] text-[var(--text-secondary)] hover:bg-[var(--elevated)]">{secretVisible?"Hide":"Reveal"}</button></div></div></section><div className="rounded-[6px] border border-[var(--border-subtle)] p-3"><p className="text-[10px] font-medium text-[var(--text-primary)]">Store it in your secrets manager</p><p className="mt-1 text-[10px] leading-4 text-[var(--text-tertiary)]">Use this value in the external service that calls your webhook. It is never included in the endpoint URL or shown again after this drawer closes.</p></div>{error&&<p role="alert" className="text-[10px] text-red-500">{error}</p>}<div className="sticky bottom-0 -mx-5 mt-auto flex justify-end border-t border-[var(--border-subtle)] bg-[var(--surface)] px-5 py-4"><button type="button" onClick={closeDialog} className="h-8 rounded-[6px] bg-[var(--accent)] px-4 text-[11px] font-medium text-white">Done, secret saved</button></div></div>}
      {dialog === "delete" && <div className="flex-1 space-y-4 p-5"><div className="rounded-[6px] border border-red-500/30 bg-red-500/5 p-3"><p className="text-[11px] font-semibold text-[var(--text-primary)]">{webhook?.name}</p><p className="mt-1 text-[10px] leading-4 text-[var(--text-secondary)]">Deleting this webhook immediately disables its endpoint. External services using it will stop triggering this workflow. This cannot be undone.</p></div>{error&&<p role="alert" className="text-[10px] text-red-500">{error}</p>}<div className="sticky bottom-0 -mx-5 mt-auto flex justify-end gap-2 border-t border-[var(--border-subtle)] bg-[var(--surface)] px-5 py-4"><button type="button" disabled={saving} onClick={closeDialog} className="h-8 rounded-[6px] border border-[var(--border-default)] px-3 text-[11px]">Cancel</button><button type="button" disabled={saving} onClick={removeWebhook} className="h-8 rounded-[6px] bg-red-600 px-3 text-[11px] font-medium text-white hover:bg-red-700">{saving?"Deleting…":"Delete webhook"}</button></div></div>}
      {dialog === "regenerate" && <div className="flex-1 space-y-4 p-5"><div className="rounded-[6px] border border-[var(--border-default)] bg-[var(--elevated)] p-3"><p className="text-[11px] font-medium text-[var(--text-primary)]">Current endpoint will be invalidated</p><code className="mt-2 block break-all font-mono text-[10px] leading-4 text-[var(--text-secondary)]">{`${endpoint.split("/hooks/")[0]}/hooks/••••••••${String(webhook.public_token || "").slice(-4)}`}</code></div><p className="text-[11px] leading-5 text-[var(--text-secondary)]">The current webhook URL will stop working after the token is regenerated. External services using it will need to be updated.</p>{error&&<p role="alert" className="text-[10px] text-red-500">{error}</p>}<div className="sticky bottom-0 -mx-5 mt-auto flex justify-end gap-2 border-t border-[var(--border-subtle)] bg-[var(--surface)] px-5 py-4"><button type="button" onClick={closeDialog} className="h-8 rounded-[6px] border border-[var(--border-default)] px-3 text-[11px]">Cancel</button><button type="button" disabled={saving} onClick={regenerate} className="h-8 rounded-[6px] bg-[var(--text-primary)] px-3 text-[11px] text-[var(--canvas)]">{saving?"Regenerating…":"Regenerate token"}</button></div></div>}
    </section></div>}
    <WebhookTestDialog open={testOpen} webhook={webhook} onClose={() => setTestOpen(false)} />
  </div>;
}

function ScheduleConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Cron Expression</FieldLabel>
        <TextInput
          value={config.cron}
          onChange={(v) => onChange("cron", v)}
          placeholder="0 9 * * 1-5"
          mono
        />
        <p className="mt-1 text-[10px] text-[var(--text-tertiary)]">
          Standard 5-field cron (min hr dom mon dow)
        </p>
      </div>
      <div>
        <FieldLabel>Timezone</FieldLabel>
        <TextInput
          value={config.timezone}
          onChange={(v) => onChange("timezone", v)}
          placeholder="UTC"
        />
      </div>
    </div>
  );
}

function ManualConfig() {
  return (
    <div className="p-3 rounded-[6px] bg-[var(--elevated)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)] leading-relaxed">
      ▶ No configuration required. This node triggers the workflow manually via the dashboard or API.
    </div>
  );
}

const connectionRowsOf = (data) => Array.isArray(data) ? data : data?.connections || data?.results || data?.data || [];

function HttpRequestConfig({ config, onChange }) {
  const [connections, setConnections] = useState([]);
  const [connectionsLoading, setConnectionsLoading] = useState(true);
  const [connectionsError, setConnectionsError] = useState(false);

  const loadConnections = async () => {
    setConnectionsLoading(true);
    setConnectionsError(false);
    try {
      const result = await listConnections();
      setConnections(connectionRowsOf(result));
    } catch {
      setConnectionsError(true);
    } finally {
      setConnectionsLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    setConnectionsLoading(true);
    setConnectionsError(false);
    listConnections().then((result) => {
      if (active) setConnections(connectionRowsOf(result));
    }).catch(() => {
      if (active) setConnectionsError(true);
    }).finally(() => {
      if (active) setConnectionsLoading(false);
    });
    return () => { active = false; };
  }, []);

  const httpConnections = connections.filter((connection) => connection.provider === "http");
  const selectedConnection = httpConnections.find((connection) => String(connection.id) === String(config.connection_id));
  const connectionBaseUrl = selectedConnection?.config?.base_url?.trim().replace(/\/+$/, "") || "";
  const configuredUrl = config.url || "";
  const requestPath = connectionBaseUrl && configuredUrl.startsWith(connectionBaseUrl)
    ? configuredUrl.slice(connectionBaseUrl.length) || "/"
    : configuredUrl;
  const handlePathChange = (path) => {
    const normalizedPath = path.trim();
    const composedUrl = connectionBaseUrl
      ? `${connectionBaseUrl}${normalizedPath ? (normalizedPath.startsWith("/") ? normalizedPath : `/${normalizedPath}`) : ""}`
      : path;
    onChange("url", composedUrl);
  };

  return (
    <div className="space-y-3">
      <section className="overflow-hidden rounded-[8px] border border-[var(--border-default)] bg-[var(--surface)]">
        <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-3 py-2.5">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-[6px] border border-sky-500/20 bg-sky-500/[0.07] text-sky-500" aria-hidden="true">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18"/></svg>
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-semibold text-[var(--text-primary)]">HTTP connection</p>
            <p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">Optional · adds a base URL and saved authentication</p>
          </div>
          <Link href="/connections" className="shrink-0 rounded-[5px] border border-[var(--border-subtle)] px-2 py-1 text-[10px] font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]">＋ Add</Link>
        </div>
        {connectionsLoading ? (
          <div className="space-y-2 p-3" aria-label="Loading HTTP connections"><div className="h-3 w-28 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-9 animate-pulse rounded-[6px] bg-[var(--elevated)]"/></div>
        ) : connectionsError ? (
          <div className="m-3 flex items-center justify-between gap-2 rounded-[6px] border border-red-500/25 bg-red-500/5 px-2.5 py-2.5">
            <p role="alert" className="text-[10px] text-red-500">Unable to load HTTP connections.</p>
            <button type="button" onClick={loadConnections} className="rounded px-2 py-1 text-[10px] font-medium text-[var(--text-secondary)] hover:bg-[var(--surface)] hover:text-[var(--text-primary)]">Retry</button>
          </div>
        ) : httpConnections.length === 0 ? (
          <div className="flex items-center gap-3 p-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--elevated)] text-[var(--text-tertiary)]" aria-hidden="true">＋</span>
            <div className="min-w-0 flex-1"><p className="text-[11px] font-medium text-[var(--text-primary)]">No HTTP connections yet</p><p className="mt-0.5 text-[10px] leading-4 text-[var(--text-tertiary)]">Add one to reuse its endpoint and authentication.</p></div>
            <Link href="/connections" className="shrink-0 text-[10px] font-semibold text-[var(--accent)] hover:underline">Create</Link>
          </div>
        ) : (
          <div className="space-y-2.5 p-3">
            <FieldLabel>Saved connections</FieldLabel>
            <select
              aria-label="HTTP request connection"
              value={config.connection_id ?? ""}
              onChange={(event) => onChange("connection_id", event.target.value || undefined)}
              className="w-full h-10 px-3 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] hover:border-[var(--border-strong)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/20 focus:outline-none transition-colors"
            >
              <option value="">No connection</option>
              {httpConnections.map((connection) => (
                <option key={connection.id} value={connection.id}>{connection.name}</option>
              ))}
            </select>
            {config.connection_id && !selectedConnection && <p className="mt-1.5 text-[10px] text-amber-600 dark:text-amber-400">The saved connection is unavailable. Choose another connection or clear the selection.</p>}
            {selectedConnection && <div className="flex min-w-0 items-center gap-2 rounded-[5px] bg-[var(--elevated)] px-2.5 py-2"><span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" aria-hidden="true"/><div className="min-w-0"><p className="truncate text-[10px] font-medium text-[var(--text-secondary)]">{selectedConnection.config?.base_url || "HTTP API"}</p><p className="mt-0.5 text-[9px] text-[var(--text-tertiary)]">{selectedConnection.auth_type === "none" ? "No authentication" : "Authentication configured"}</p></div></div>}
          </div>
        )}
      </section>
      <div>
        <FieldLabel>Method</FieldLabel>
        <SelectInput
          value={config.method}
          onChange={(v) => onChange("method", v)}
          options={[
            { value: "GET", label: "GET" },
            { value: "POST", label: "POST" },
            { value: "PUT", label: "PUT" },
            { value: "PATCH", label: "PATCH" },
            { value: "DELETE", label: "DELETE" },
          ]}
        />
      </div>
      <div>
        <FieldLabel>{selectedConnection ? "Request path" : "URL"}</FieldLabel>
        {selectedConnection && <div className="mb-1.5 flex min-w-0 items-center overflow-hidden rounded-[5px] border border-[var(--border-subtle)] bg-[var(--elevated)] font-mono text-[10px] leading-4"><span className="shrink-0 border-r border-[var(--border-subtle)] px-2 py-1.5 text-[var(--text-tertiary)]">BASE</span><span className="truncate px-2 py-1.5 text-[var(--text-secondary)]" title={connectionBaseUrl}>{connectionBaseUrl || "Base URL is not configured"}</span></div>}
        <div className="flex h-8 overflow-hidden rounded-[6px] border border-[var(--border-default)] bg-[var(--input-bg)] focus-within:border-[var(--border-strong)] focus-within:ring-1 focus-within:ring-[var(--accent)]">
          {selectedConnection && <span className="flex shrink-0 items-center border-r border-[var(--border-default)] px-2 text-[11px] font-mono text-[var(--text-tertiary)]">/</span>}
          <input
            type="text"
            value={selectedConnection ? requestPath.replace(/^\/+/, "") : config.url ?? ""}
            onChange={(event) => selectedConnection ? handlePathChange(event.target.value) : onChange("url", event.target.value)}
            placeholder={selectedConnection ? "v1/orders" : "https://api.example.com/endpoint"}
            aria-label={selectedConnection ? "HTTP request path" : "HTTP request URL"}
            className="h-full min-w-0 flex-1 bg-transparent px-2.5 text-[12px] font-mono text-[var(--text-primary)] placeholder:text-[var(--text-disabled)] outline-none"
          />
        </div>
        <p className="mt-1 text-[10px] text-[var(--text-tertiary)]">{selectedConnection ? "The saved connection supplies the base URL and authentication." : "Select a saved connection to reuse its base URL and authentication."}</p>
      </div>
      <div>
        <FieldLabel>Additional headers</FieldLabel>
        <TextareaInput
          value={config.headers}
          onChange={(v) => onChange("headers", v)}
          placeholder={"Content-Type: application/json\nAuthorization: Bearer {{token}}"}
          rows={2}
          mono
        />
        <p className="mt-1 text-[10px] text-[var(--text-tertiary)]">One per line: Name: Value. Connection authentication is added separately.</p>
      </div>
      <div>
        <FieldLabel>Body</FieldLabel>
        <TextareaInput
          value={config.body}
          onChange={(v) => onChange("body", v)}
          placeholder='{"key": "value"}'
          rows={3}
          mono
        />
      </div>
    </div>
  );
}

function EmailConfig({ config, onChange }) {
  const [connections, setConnections] = useState([]);
  const [connectionsLoading, setConnectionsLoading] = useState(true);
  const [connectionsError, setConnectionsError] = useState(false);

  const loadGmailConnections = async () => {
    setConnectionsLoading(true);
    setConnectionsError(false);
    try {
      const result = await listConnections();
      setConnections(connectionRowsOf(result).filter((connection) => connection.provider === "gmail"));
    } catch {
      setConnectionsError(true);
    } finally {
      setConnectionsLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    listConnections().then((result) => {
      if (active) setConnections(connectionRowsOf(result).filter((connection) => connection.provider === "gmail"));
    }).catch(() => {
      if (active) setConnectionsError(true);
    }).finally(() => {
      if (active) setConnectionsLoading(false);
    });
    return () => { active = false; };
  }, []);

  const selectedGmail = connections.find((connection) => String(connection.id) === String(config.connection_id));

  return (
    <div className="space-y-3">
      <section className="overflow-hidden rounded-[8px] border border-[var(--border-default)] bg-[var(--surface)]">
        <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] px-3 py-2.5">
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-[6px] border border-red-500/20 bg-red-500/[0.06] text-red-500" aria-hidden="true">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></svg>
          </span>
          <div className="min-w-0 flex-1"><p className="text-[11px] font-semibold text-[var(--text-primary)]">Gmail account</p><p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">Choose the connected account that sends this email.</p></div>
          <Link href="/connections" className="shrink-0 rounded-[5px] border border-[var(--border-subtle)] px-2 py-1 text-[10px] font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]">＋ Add</Link>
        </div>
        {connectionsLoading ? <div className="space-y-2 p-3" aria-label="Loading Gmail accounts"><div className="h-3 w-24 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-9 animate-pulse rounded-[6px] bg-[var(--elevated)]"/></div> : connectionsError ? (
          <div className="m-3 flex items-center justify-between gap-2 rounded-[6px] border border-red-500/25 bg-red-500/5 px-2.5 py-2.5"><p role="alert" className="text-[10px] text-red-500">Unable to load Gmail accounts.</p><button type="button" onClick={loadGmailConnections} className="rounded px-2 py-1 text-[10px] font-medium text-[var(--text-secondary)] hover:bg-[var(--surface)]">Retry</button></div>
        ) : connections.length === 0 ? (
          <div className="flex items-center gap-3 p-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--elevated)] text-[var(--text-tertiary)]" aria-hidden="true">＋</span><div className="min-w-0 flex-1"><p className="text-[11px] font-medium text-[var(--text-primary)]">No Gmail accounts connected</p><p className="mt-0.5 text-[10px] leading-4 text-[var(--text-tertiary)]">Connect Gmail to send email from this workflow.</p></div><Link href="/connections" className="shrink-0 text-[10px] font-semibold text-[var(--accent)] hover:underline">Connect</Link></div>
        ) : (
          <div className="space-y-2.5 p-3"><FieldLabel>Connected accounts</FieldLabel><select aria-label="Gmail sending account" value={config.connection_id ?? ""} onChange={(event) => onChange("connection_id", event.target.value || undefined)} className="h-10 w-full rounded-[6px] border border-[var(--border-default)] bg-[var(--input-bg)] px-3 text-[12px] text-[var(--text-primary)] transition-colors hover:border-[var(--border-strong)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/20"><option value="">Select a Gmail account</option>{connections.map((connection) => <option key={connection.id} value={connection.id}>{connection.config?.email || connection.name}</option>)}</select>{config.connection_id && !selectedGmail && <p className="text-[10px] text-amber-600 dark:text-amber-400">This Gmail account is unavailable. Choose another account.</p>}{selectedGmail && <div className="flex items-center gap-2 rounded-[5px] bg-[var(--elevated)] px-2.5 py-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true"/><p className="truncate text-[10px] text-[var(--text-secondary)]">Connected · {selectedGmail.config?.email || selectedGmail.name}</p></div>}</div>
        )}
      </section>
      <div>
        <FieldLabel>To Email</FieldLabel>
        <TextInput
          value={config.to}
          onChange={(v) => onChange("to", v)}
          placeholder="recipient@example.com"
        />
      </div>
      <div>
        <FieldLabel>Subject</FieldLabel>
        <TextInput
          value={config.subject}
          onChange={(v) => onChange("subject", v)}
          placeholder="Workflow Notification"
        />
      </div>
      <div>
        <FieldLabel>Message Body</FieldLabel>
        <TextareaInput
          value={config.body}
          onChange={(v) => onChange("body", v)}
          placeholder="Your automated message here."
          rows={3}
        />
      </div>
    </div>
  );
}

function RefundConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Charge / Order ID</FieldLabel>
        <TextInput
          value={config.charge_id}
          onChange={(v) => onChange("charge_id", v)}
          placeholder="ch_12345"
          mono
        />
      </div>
      <div>
        <FieldLabel>Reason</FieldLabel>
        <SelectInput
          value={config.reason}
          onChange={(v) => onChange("reason", v)}
          options={[
            { value: "requested_by_customer", label: "Requested by customer" },
            { value: "duplicate", label: "Duplicate charge" },
            { value: "fraudulent", label: "Fraudulent" },
          ]}
        />
      </div>
    </div>
  );
}

function AIConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Prompt / Instruction</FieldLabel>
        <TextareaInput
          value={config.prompt}
          onChange={(v) => onChange("prompt", v)}
          placeholder="Describe what the AI should do..."
          rows={4}
        />
      </div>
      <div>
        <FieldLabel>Model</FieldLabel>
        <SelectInput
          value={config.model}
          onChange={(v) => onChange("model", v)}
          options={[
            { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
            { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
            { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
          ]}
        />
      </div>
    </div>
  );
}

function RAGConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Knowledge Base ID</FieldLabel>
        <TextInput
          value={config.knowledge_base}
          onChange={(v) => onChange("knowledge_base", v)}
          placeholder="kb_customer_docs"
          mono
        />
      </div>
      <div>
        <FieldLabel>Query</FieldLabel>
        <TextInput
          value={config.query}
          onChange={(v) => onChange("query", v)}
          placeholder="{{input.message}}"
          mono
        />
      </div>
      <div>
        <FieldLabel>Top K Results</FieldLabel>
        <TextInput
          value={String(config.top_k ?? 5)}
          onChange={(v) => onChange("top_k", Number.parseInt(v, 10) || 5)}
          placeholder="5"
          mono
        />
      </div>
    </div>
  );
}

function ConditionConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Field / Variable</FieldLabel>
        <TextInput
          value={config.field}
          onChange={(v) => onChange("field", v)}
          placeholder="status_code"
          mono
        />
      </div>
      <div>
        <FieldLabel>Operator</FieldLabel>
        <SelectInput
          value={config.operator}
          onChange={(v) => onChange("operator", v)}
          options={[
            { value: "equals", label: "Equals (==)" },
            { value: "not_equals", label: "Not Equals (!=)" },
            { value: "contains", label: "Contains" },
            { value: "not_contains", label: "Does not contain" },
            { value: "greater_than", label: "Greater Than (>)" },
            { value: "less_than", label: "Less Than (<)" },
            { value: "is_empty", label: "Is empty" },
            { value: "is_not_empty", label: "Is not empty" },
          ]}
        />
      </div>
      <div>
        <FieldLabel>Value</FieldLabel>
        <TextInput
          value={config.value}
          onChange={(v) => onChange("value", v)}
          placeholder="200"
          mono
        />
      </div>
    </div>
  );
}

function ApprovalConfig({ config, onChange }) {
  return (
    <div className="space-y-3">
      <div>
        <FieldLabel>Approver Email</FieldLabel>
        <TextInput
          value={config.approver}
          onChange={(v) => onChange("approver", v)}
          placeholder="admin@company.com"
        />
      </div>
      <div>
        <FieldLabel>Timeout (hours)</FieldLabel>
        <TextInput
          value={String(config.timeout_hours ?? 24)}
          onChange={(v) => onChange("timeout_hours", Number.parseInt(v, 10) || 24)}
          placeholder="24"
          mono
        />
      </div>
      <div>
        <FieldLabel>Message</FieldLabel>
        <TextareaInput
          value={config.message}
          onChange={(v) => onChange("message", v)}
          placeholder="Please review and approve this request."
          rows={2}
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NodeInspector
// ─────────────────────────────────────────────────────────────────────────────
export default function NodeInspector({
  selectedNode,
  onUpdateNode,
  onDeleteNode,
  onClose,
  isReadOnly = false,
  workflowId,
  workflowVersionId,
  className = "",
}) {
  const [formData, setFormData] = useState({});
  const [nodeName, setNodeName] = useState("");
  const [hasLocalChanges, setHasLocalChanges] = useState(false);
  const [webhookGuideOpen, setWebhookGuideOpen] = useState(false);

  useEffect(() => {
    if (selectedNode) {
      setNodeName(selectedNode.data?.label ?? selectedNode.data?.name ?? "");
      setFormData({ ...(selectedNode.data?.config ?? {}) });
      setHasLocalChanges(false);
    } else {
      setNodeName("");
      setFormData({});
      setHasLocalChanges(false);
    }
  }, [selectedNode?.id, workflowVersionId]); // Same node ids are reused across workflow versions.

  // Empty state
  if (!selectedNode) {
    return (
      <div className="w-80 bg-[var(--surface)] border-l border-[var(--border-subtle)] flex flex-col h-full select-none shrink-0 font-sans p-6 items-center justify-center text-center relative z-20 animate-in slide-in-from-right duration-150">
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            title="Close Inspector"
            className="absolute top-3 right-3 p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors cursor-pointer"
          >
            <XIcon className="w-4 h-4 stroke-[1.5]" />
          </button>
        )}
        <div className="w-10 h-10 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--text-tertiary)] mb-3">
          <SettingsIcon className="w-5 h-5 stroke-[1.5]" />
        </div>
        <h4 className="text-[14px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
          Node Inspector
        </h4>
        <p className="text-[12px] text-[var(--text-tertiary)] leading-relaxed max-w-[200px]">
          Click a node on the canvas to configure its settings.
        </p>
      </div>
    );
  }

  const typeId = selectedNode.data?.typeId ?? "custom";
  const def = getNodeDefinition(typeId);

  const handleFieldChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasLocalChanges(true);
  };

  const handleSave = (e) => {
    e?.preventDefault();
    if (isReadOnly) return;
    if (onUpdateNode) {
      onUpdateNode(selectedNode.id, {
        label: nodeName,
        name: nodeName,
        config: formData,
      });
      setHasLocalChanges(false);
    }
  };

  // Determine config panel
  const renderConfigPanel = () => {
    switch (typeId) {
      case "trigger.webhook":
        return <WebhookConfig config={formData} workflowId={workflowId} workflowVersionId={workflowVersionId} nodeId={selectedNode.id} isReadOnly={isReadOnly} onOpenGuide={() => setWebhookGuideOpen(true)} onAssociate={(webhook) => {
          if (isReadOnly) return;
          const nextConfig = webhook
            ? { ...formData, webhook_id: webhook.id, method: webhook.method || "POST", event_name: webhook.event_name || "", setup_required: false }
            : { ...formData, webhook_id: undefined, method: "POST", event_name: "", setup_required: true };
          if (!webhook) {
            delete nextConfig.public_token;
            delete nextConfig.secret;
            delete nextConfig.endpoint;
            delete nextConfig.url;
            delete nextConfig.path;
          }
          setFormData(nextConfig);
          setHasLocalChanges(true);
          if (onUpdateNode) onUpdateNode(selectedNode.id, { config: nextConfig });
        }} />;
      case "trigger.schedule":
        return <ScheduleConfig config={formData} onChange={handleFieldChange} />;
      case "trigger.manual":
        return <ManualConfig />;
      case "action.http_request":
        return <HttpRequestConfig config={formData} onChange={handleFieldChange} />;
      case "action.email":
        return <EmailConfig config={formData} onChange={handleFieldChange} />;
      case "action.refund":
        return <RefundConfig config={formData} onChange={handleFieldChange} />;
      case "ai.decision":
      case "ai.generate":
        return <AIConfig config={formData} onChange={handleFieldChange} />;
      case "ai.rag_search":
        return <RAGConfig config={formData} onChange={handleFieldChange} />;
      case "logic.condition":
        return <ConditionConfig config={formData} onChange={handleFieldChange} />;
      case "human.approval":
        return <ApprovalConfig config={formData} onChange={handleFieldChange} />;
      default:
        return (
          <div className="p-3 rounded-[6px] bg-[var(--elevated)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)]">
            No configuration fields for this node type.
          </div>
        );
    }
  };

  // Category accent color
  const getCategoryColor = () => {
    if (typeId.startsWith("trigger.")) return "bg-[#4F46E5]/10 text-[#4F46E5] border-[#4F46E5]/20";
    if (typeId.startsWith("action.")) return "bg-[#0EA5E9]/10 text-[#0EA5E9] border-[#0EA5E9]/20";
    if (typeId.startsWith("ai.")) return "bg-[#8B5CF6]/10 text-[#8B5CF6] border-[#8B5CF6]/20";
    if (typeId.startsWith("logic.") || typeId.startsWith("human.")) return "bg-[#D29922]/10 text-[#D29922] border-[#D29922]/20";
    return "bg-[var(--elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]";
  };

  return (
    <div className={`w-80 bg-[var(--surface)] border-l border-[var(--border-subtle)] flex flex-col h-full min-h-0 overflow-x-hidden overflow-y-auto overscroll-contain select-none shrink-0 font-sans z-20 animate-in slide-in-from-right duration-150 ${className}`}>
      {/* Header */}
      <div className="px-3 py-2.5 border-b border-[var(--border-subtle)] space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-[16px] shrink-0">{def.icon}</span>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-[var(--text-primary)] truncate">
                {typeId === "trigger.webhook" ? "Webhook trigger" : nodeName || def.name}
              </div>
              <div className="text-[9px] font-mono text-[var(--text-tertiary)] truncate">
                {typeId}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {typeId === "trigger.webhook" && <button type="button" onClick={() => setWebhookGuideOpen(true)} title="How to use this webhook" aria-label="How to use this webhook" className="grid h-6 w-6 place-items-center rounded-full border border-[var(--border-default)] font-mono text-[10px] font-semibold text-[var(--text-secondary)] transition hover:border-cyan-500/50 hover:bg-cyan-500/10 hover:text-cyan-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/40">?</button>}
            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded-[4px] border shrink-0 ${getCategoryColor()}`}>
              {def.category}
            </span>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                title="Close Inspector"
                className="p-1 rounded text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors cursor-pointer"
              >
                <XIcon className="w-4 h-4 stroke-[1.5]" />
              </button>
            )}
          </div>
        </div>

        {/* Node ID badge */}
        <div className="flex items-center gap-1">
          {typeId !== "trigger.webhook" && <span className="text-[9px] font-mono text-[var(--text-tertiary)] bg-[var(--elevated)] px-1.5 py-0.5 rounded border border-[var(--border-subtle)]">
            id: {selectedNode.data?.nodeId ?? selectedNode.id}
          </span>}
          {hasLocalChanges && !isReadOnly && (
            <span className="text-[9px] font-mono text-[#D29922] bg-[#D29922]/10 px-1.5 py-0.5 rounded border border-[#D29922]/20">
              unsaved
            </span>
          )}
        </div>
      </div>

      {/* Config form */}
      <form onSubmit={handleSave} className="shrink-0 p-3">
        <div className="space-y-3">
        {/* Node label */}
        {typeId !== "trigger.webhook" && <div>
          <FieldLabel>Node Label</FieldLabel>
          <input
            type="text"
            value={nodeName}
            onChange={(e) => {
              setNodeName(e.target.value);
              setHasLocalChanges(true);
            }}
            disabled={isReadOnly}
            className="w-full h-8 px-2.5 text-[12px] bg-[var(--input-bg)] text-[var(--text-primary)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
          />
        </div>}

        {/* Per-type config */}
        <div className={`${typeId === "trigger.webhook" ? "" : "pt-2 border-t border-[var(--border-subtle)]"} space-y-3`}>
          {typeId !== "trigger.webhook" && <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-tertiary)]">
            Configuration
          </div>}
          {isReadOnly ? (
            <div className="opacity-60 pointer-events-none">
              {renderConfigPanel()}
            </div>
          ) : (
            renderConfigPanel()
          )}
        </div>

        </div>

        {/* Actions follow the configuration in the inspector's single scroll area. */}
        {!isReadOnly && (
          <div className="mt-3 space-y-2 border-t border-[var(--border-subtle)] pt-3">
            <button
              type="submit"
              className={`w-full h-8 px-3 rounded-[6px] font-medium text-[12px] transition-all duration-100 ease-out flex items-center justify-center gap-1.5 cursor-pointer shadow-none ${
                hasLocalChanges
                  ? "bg-[#4F46E5] hover:bg-[#6366F1] text-white"
                  : "bg-[var(--elevated)] hover:bg-[var(--border-subtle)] text-[var(--text-secondary)] border border-[var(--border-default)]"
              }`}
            >
              <SaveIcon className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>{hasLocalChanges ? "Apply node changes" : "Node changes saved"}</span>
            </button>

            <button
              type="button"
              onClick={() => onDeleteNode && onDeleteNode(selectedNode.id)}
              className="w-full h-8 px-3 rounded-[6px] border border-red-500/20 bg-red-500/5 hover:bg-red-500/15 text-red-600 dark:text-red-400 font-medium text-[12px] transition-all duration-100 ease-out flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <TrashIcon className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>Delete Node</span>
            </button>
          </div>
        )}
      </form>
      <WebhookUsageGuide open={webhookGuideOpen} onClose={() => setWebhookGuideOpen(false)} />
    </div>
  );
}
