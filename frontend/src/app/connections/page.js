"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import { useAuth } from "@/context/AuthContext";
import { createConnection, deleteConnection, listConnections, startGmailOAuth, testConnection, updateConnection } from "@/services/connections";

const rowsOf = (data) => Array.isArray(data) ? data : data?.connections || data?.results || data?.data || [];
const authLabels = { none: "No authentication", bearer: "Bearer token", api_key_header: "API key · Header", api_key_query: "API key · Query parameter" };
const authTypes = ["none", "bearer", "api_key_header", "api_key_query"];
const initialForm = () => ({ name: "", auth_type: "none", base_url: "", test_url: "", auth_header: "", auth_param: "", credential: "" });
const inputClass = "h-9 w-full rounded-[6px] border border-[var(--border-default)] bg-[var(--input-bg)] px-3 text-[13px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-disabled)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)]/40 disabled:opacity-50";
const buttonClass = "inline-flex h-9 items-center justify-center gap-1.5 rounded-[6px] border px-3 text-[13px] font-medium transition-colors duration-100 disabled:cursor-not-allowed disabled:opacity-50";
const primaryClass = `${buttonClass} border-transparent bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]`;
const secondaryClass = `${buttonClass} border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--elevated)]`;

function Modal({ title, description, onClose, children, wide = false }) {
  useEffect(() => {
    const handleKey = (event) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);
  return <div className="connection-overlay fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section role="dialog" aria-modal="true" aria-labelledby="connection-dialog-title" className={`connection-dialog max-h-[90vh] w-full ${wide ? "max-w-xl" : "max-w-md"} overflow-y-auto rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-5`}><div className="mb-5 flex items-start justify-between gap-4"><div><h2 id="connection-dialog-title" className="text-[18px] font-semibold">{title}</h2>{description && <p className="mt-1 text-[13px] leading-5 text-[var(--text-secondary)]">{description}</p>}</div><button type="button" onClick={onClose} aria-label="Close dialog" className="rounded p-1 text-[var(--text-tertiary)] transition-colors duration-100 hover:bg-[var(--elevated)]">×</button></div>{children}</section></div>;
}

function Field({ label, htmlFor, error, helper, children }) {
  return <div className="grid gap-1.5"><label htmlFor={htmlFor} className="text-[12px] font-medium text-[var(--text-secondary)]">{label}</label>{children}{helper && <p className="text-[11px] leading-4 text-[var(--text-tertiary)]">{helper}</p>}{error && <p role="alert" className="text-[12px] text-red-500">{error}</p>}</div>;
}

function safeResponse(value) {
  const sensitive = /^(token|access_token|refresh_token|api_key|secret|password|authorization)$/i;
  const clean = (item) => {
    if (Array.isArray(item)) return item.map(clean);
    if (item && typeof item === "object") return Object.fromEntries(Object.entries(item).map(([key, child]) => [key, sensitive.test(key) ? "[REDACTED]" : clean(child)]));
    return item;
  };
  try { return JSON.stringify(clean(value), null, 2); } catch { return "Response could not be displayed."; }
}

function GmailIcon({ className = "h-5 w-5" }) {
  return <img className={className} src="/brand/gmail.png" alt="Gmail" />;
}
export default function ConnectionsPage() {
  const { isInitializing } = useAuth();
  const searchParams = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [reload, setReload] = useState(0);
  const [query, setQuery] = useState("");
  const [authFilter, setAuthFilter] = useState("all");
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [credentialVisible, setCredentialVisible] = useState(false);
  const [replaceCredential, setReplaceCredential] = useState(false);
  const [showTestUrl, setShowTestUrl] = useState(false);
  const [saving, setSaving] = useState(false);
  const [connectingGmail, setConnectingGmail] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [testingId, setTestingId] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [notice, setNotice] = useState("");
  const [openMenu, setOpenMenu] = useState(null);

  const refresh = useCallback(() => setReload((value) => value + 1), []);
  const flash = useCallback((message) => { setNotice(message); window.setTimeout(() => setNotice(""), 2800); }, []);

  useEffect(() => { document.title = "Connections | Relay"; }, []);
  useEffect(() => {
    const gmailStatus = searchParams.get("gmail");
    if (gmailStatus === "connected") {
      flash("Gmail connected successfully.");
      refresh();
      window.history.replaceState({}, "", "/connections");
    } else if (gmailStatus === "error") {
      setNotice("Unable to connect Gmail. Please try again.");
      window.setTimeout(() => setNotice(""), 3500);
      window.history.replaceState({}, "", "/connections");
    }
  }, [searchParams, flash, refresh]);
  useEffect(() => {
    if (isInitializing) return;
    let alive = true;
    setLoading(true);
    listConnections().then((data) => { if (alive) { setItems(rowsOf(data)); setLoadError(false); } }).catch(() => { if (alive) setLoadError(true); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [isInitializing, reload]);

  const filtered = useMemo(() => items.filter((item) => {
    const matchesQuery = `${item.name || ""} ${item.provider || ""}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesQuery && (authFilter === "all" || item.auth_type === authFilter);
  }), [items, query, authFilter]);

  const closeModal = useCallback(() => { if (!saving && !deleting) { setModal(null); setErrors({}); setCredentialVisible(false); setTestResult(null); } }, [saving, deleting]);

  const openCreate = () => { setSelected(null); setTestResult(null); setForm(initialForm()); setErrors({}); setReplaceCredential(true); setCredentialVisible(false); setShowTestUrl(false); setModal("create"); };
  const connectGmail = async () => {
    setConnectingGmail(true);
    setErrors({});
    try {
      window.location.assign(startGmailOAuth());
    } catch {
      setConnectingGmail(false);
      setErrors({ api: "Unable to connect Gmail. Please try again." });
    }
  };
  const openEdit = (item) => {
    if (item.provider === "gmail") return;
    setTestResult(null);
    const config = item.config || {};
    setSelected(item);
    setForm({ name: item.name || "", auth_type: item.auth_type || "none", base_url: config.base_url || "", test_url: config.test_url || "", auth_header: config.auth_header || "", auth_param: config.auth_param || "", credential: "" });
    setShowTestUrl(Boolean(config.test_url));
    setErrors({}); setReplaceCredential(false); setCredentialVisible(false); setModal("edit"); setOpenMenu(null);
  };

  const showDetails = (item) => { if (selected?.id !== item.id) setTestResult(null); setSelected(item); setModal("details"); setOpenMenu(null); setErrors({}); };

  const changeAuth = (value) => {
    setForm((current) => ({ ...current, auth_type: value, credential: "", auth_header: value === "api_key_header" ? current.auth_header : "", auth_param: value === "api_key_query" ? current.auth_param : "" }));
    if (selected) setReplaceCredential(value !== "none");
    setCredentialVisible(false);
  };

  const submit = async (event) => {
    event.preventDefault();
    const nextErrors = {};
    if (!form.name.trim() || form.name.trim().length > 255) nextErrors.name = "Enter a name between 1 and 255 characters.";
    for (const field of ["base_url", ...(form.test_url.trim() ? ["test_url"] : [])]) {
      try { const parsed = new URL(form[field]); if (!["http:", "https:"].includes(parsed.protocol)) throw new Error(); }
      catch { nextErrors[field] = "Enter a valid HTTP or HTTPS URL."; }
    }
    const needsCredential = form.auth_type !== "none" && (modal === "create" || (replaceCredential && form.auth_type !== selected?.auth_type));
    if (needsCredential && !form.credential.trim()) nextErrors.credential = "Enter a credential.";
    if (form.auth_type === "api_key_header" && !form.auth_header.trim()) nextErrors.auth_header = "Enter a header name.";
    if (form.auth_type === "api_key_query" && !form.auth_param.trim()) nextErrors.auth_param = "Enter a query parameter name.";
    if (Object.keys(nextErrors).length) { setErrors(nextErrors); return; }

    setSaving(true); setErrors({});
    const config = { base_url: form.base_url.trim(), test_url: form.test_url.trim() };
    if (form.auth_type === "api_key_header") config.auth_header = form.auth_header.trim();
    if (form.auth_type === "api_key_query") config.auth_param = form.auth_param.trim();
    const editing = modal === "edit";
    const payload = editing ? {} : { name: form.name.trim(), provider: "http", auth_type: form.auth_type, credential: form.auth_type === "none" ? null : form.credential.trim(), config };
    if (editing && form.name.trim() !== (selected.name || "")) payload.name = form.name.trim();
    if (editing && (form.auth_type !== selected.auth_type || config.base_url !== (selected.config?.base_url || "") || config.test_url !== (selected.config?.test_url || "") || config.auth_header !== (selected.config?.auth_header || undefined) || config.auth_param !== (selected.config?.auth_param || undefined))) {
      payload.auth_type = form.auth_type;
      payload.config = config;
    }
    if (editing && replaceCredential && form.auth_type !== "none" && form.credential.trim()) payload.credential = form.credential.trim();
    if (editing && form.auth_type === "none" && selected.auth_type !== "none") payload.credential = null;
    try {
      if (editing) { if (Object.keys(payload).length) await updateConnection(selected.id, payload); setModal(null); flash("Connection updated"); }
      else { await createConnection(payload); setModal(null); flash("Connection created"); }
      setForm(initialForm()); setReplaceCredential(false); setCredentialVisible(false); refresh();
    } catch { setErrors({ api: `Unable to ${editing ? "update" : "create"} connection. Check the details and try again.` }); }
    finally { setSaving(false); }
  };

  const runTest = async (item) => {
    setOpenMenu(null); setTestingId(item.id); setTestResult(null);
    try {
      const result = await testConnection(item.id);
      setTestResult({ connectionId: item.id, success: Boolean(result?.success), statusCode: result?.status_code, message: result?.message, response: result?.response });
    } catch (error) {
      setTestResult({ connectionId: item.id, success: false, message: "Unable to reach the test endpoint. Try again.", response: null, statusCode: null, network: true });
    } finally { setTestingId(null); setModal((current) => current === "details" ? "details" : "test"); }
  };

  const remove = async () => {
    if (!selected) return;
    setDeleting(true); setErrors({});
    try { await deleteConnection(selected.id); setItems((current) => current.filter((item) => item.id !== selected.id)); setModal(null); flash("Connection deleted"); }
    catch { setErrors({ api: "Unable to delete connection. Try again." }); }
    finally { setDeleting(false); }
  };

  return <ProtectedRoute><DashboardShell pageTitle="Connections"><div className="mx-auto w-full max-w-7xl space-y-6">
    <header className="flex flex-col gap-4 border-b border-[var(--border-subtle)] pb-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="mb-2 text-[11px] font-medium uppercase tracking-[.16em] text-[var(--text-tertiary)]">Workspace integrations</p><h1 className="text-[26px] font-semibold leading-[32px] tracking-tight">Connections</h1><p className="mt-1 text-[13px] text-[var(--text-secondary)]">Connect the services your workflows rely on.</p></div><button type="button" onClick={openCreate} className={`${primaryClass} shrink-0`}><span aria-hidden="true">＋</span>Add connection</button></header>

    {!loading && !loadError && <section className="flex flex-col gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-3 sm:flex-row sm:items-center"><label className="relative min-w-0 flex-1"><span aria-hidden="true" className="absolute left-3 top-2 text-[var(--text-tertiary)]">⌕</span><input aria-label="Search connections" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search connections..." className={`${inputClass} pl-9`} /></label><div className="flex items-center gap-2"><span className="text-[11px] text-[var(--text-tertiary)]">Authentication</span><select aria-label="Filter by authentication" value={authFilter} onChange={(event) => setAuthFilter(event.target.value)} className={`${inputClass} sm:w-48`}><option value="all">All types</option>{authTypes.map((type) => <option key={type} value={type}>{authLabels[type]}</option>)}</select></div><span className="whitespace-nowrap text-[11px] text-[var(--text-tertiary)]">{filtered.length} {filtered.length === 1 ? "connection" : "connections"}</span></section>}

    {loading && <div className="overflow-x-auto rounded-lg border border-[var(--border-subtle)]"><table className="w-full min-w-[760px] text-left"><thead className="bg-[var(--elevated)]"><tr>{["Name", "Provider", "Authentication", "Base URL", "Created", ""].map((title, index) => <th key={index} className="h-10 px-4 text-[10px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">{title}</th>)}</tr></thead><tbody>{[0,1,2,3].map((row) => <tr key={row} className="border-t border-[var(--border-subtle)]">{[0,1,2,3,4,5].map((cell) => <td key={cell} className="px-4 py-4"><div className={`h-3 animate-pulse rounded bg-[var(--elevated)] ${cell === 3 ? "w-48" : "w-24"}`} /></td>)}</tr>)}</tbody></table></div>}

    {loadError && !loading && <div className="rounded-md border border-[var(--border-subtle)] p-8 text-center"><h2 className="text-[14px] font-semibold">Unable to load connections</h2><p className="mt-1 text-[13px] text-[var(--text-secondary)]">We couldn’t retrieve your connections. Try again.</p><button type="button" onClick={refresh} className={`${secondaryClass} mt-4`}>Retry</button></div>}

    {!loading && !loadError && items.length === 0 && <div className="rounded-md border border-dashed border-[var(--border-default)] px-6 py-16 text-center"><div className="mx-auto mb-3 grid h-9 w-9 place-items-center rounded-md border border-[var(--border-subtle)] text-[var(--text-secondary)]" aria-hidden="true"><GmailIcon /></div><h2 className="text-[16px] font-semibold">No connections yet</h2><p className="mx-auto mt-2 max-w-sm text-[13px] leading-5 text-[var(--text-secondary)]">Connect Gmail or create an API connection to use external services in your workflows.</p><button type="button" onClick={openCreate} className={`${primaryClass} mt-5`}>＋ Add connection</button></div>}

    {!loading && !loadError && items.length > 0 && filtered.length === 0 && <div className="rounded-md border border-[var(--border-subtle)] px-6 py-14 text-center"><h2 className="text-[14px] font-semibold">No connections found</h2><p className="mt-1 text-[13px] text-[var(--text-secondary)]">No connections match your search and filters.</p><button type="button" onClick={() => { setQuery(""); setAuthFilter("all"); }} className="mt-3 text-[13px] text-[var(--accent)]">Clear filters</button></div>}

    {!loading && !loadError && filtered.length > 0 && <section aria-label="Your connections" className="grid gap-3 sm:grid-cols-2">{filtered.map((item) => { const isGmail = item.provider === "gmail"; return <article key={item.id} className="group relative flex min-h-[118px] items-start gap-3.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--elevated)]"><div className="grid h-12 w-12 shrink-0 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--input-bg)] text-[var(--text-secondary)]">{isGmail ? <GmailIcon /> : <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0-18"/></svg>}</div><button type="button" onClick={() => showDetails(item)} className="min-w-0 flex-1 text-left"><span className="flex items-center gap-2"><strong className="truncate text-[14px] font-medium text-[var(--text-primary)]">{item.name}</strong><span className="shrink-0 rounded-full border border-[var(--border-subtle)] px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-[var(--text-tertiary)]">{isGmail ? "Gmail" : (item.provider || "http").toUpperCase()}</span></span><span className="mt-1.5 block truncate text-[12px] text-[var(--text-secondary)]" title={isGmail ? item.config?.email : item.config?.base_url}>{isGmail ? (item.config?.email || "Gmail account") : (item.config?.base_url || "External API connection")}</span><span className="mt-1.5 block text-[11px] text-[var(--text-tertiary)]">{isGmail ? "Google OAuth" : (authLabels[item.auth_type] || item.auth_type)}{item.created_at ? ` · Added ${new Date(item.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}` : ""}</span><span className="mt-1.5 inline-flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)]"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true"/>Connected</span></button><div className="relative shrink-0"><button type="button" aria-label={`Manage ${item.name}`} aria-expanded={openMenu === item.id} onClick={() => setOpenMenu(openMenu === item.id ? null : item.id)} className="grid h-8 w-8 place-items-center rounded-md border border-[var(--border-subtle)] bg-[var(--elevated)] text-[18px] leading-none text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]">···</button>{openMenu === item.id && <div className="absolute right-0 top-10 z-20 w-44 rounded-md border border-[var(--border-default)] bg-[var(--surface)] p-1 shadow-xl"><button type="button" onClick={() => showDetails(item)} className="block w-full rounded px-2 py-1.5 text-left text-[12px] hover:bg-[var(--elevated)]">View configuration</button>{!isGmail && <><button type="button" onClick={() => openEdit(item)} className="block w-full rounded px-2 py-1.5 text-left text-[12px] hover:bg-[var(--elevated)]">Edit</button><button type="button" disabled={testingId === item.id} onClick={() => runTest(item)} className="block w-full rounded px-2 py-1.5 text-left text-[12px] hover:bg-[var(--elevated)] disabled:opacity-50">{testingId === item.id ? "Testing…" : "Test connection"}</button></>}<button type="button" onClick={() => { setSelected(item); setErrors({}); setOpenMenu(null); setModal("delete"); }} className="block w-full rounded px-2 py-1.5 text-left text-[12px] text-red-500 hover:bg-[var(--elevated)]">Disconnect</button></div>}</div></article>; })}</section>}

    {notice && <div role="status" className="connection-toast fixed bottom-5 right-5 z-[120] rounded-md border border-[var(--border-default)] bg-[var(--surface)] px-4 py-2.5 text-[13px] text-[var(--text-primary)]"><span className="mr-2 inline-block h-1.5 w-1.5 rounded-full bg-[var(--accent)]" aria-hidden="true" />{notice}</div>}

    {modal === "create" && <Modal title="Add connection" description="Connect a service to use it in your workflows." onClose={closeModal} wide><div className="space-y-4"><article className="flex flex-col gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-4 sm:flex-row sm:items-center"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--input-bg)]"><GmailIcon className="h-6 w-6" /></div><div className="min-w-0 flex-1"><h3 className="text-[14px] font-medium text-[var(--text-primary)]">Gmail</h3><p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">Connect your Gmail account to send emails from Relay workflows.</p></div><button type="button" onClick={connectGmail} disabled={connectingGmail} className={`${primaryClass} shrink-0`}>{connectingGmail ? <><span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" aria-hidden="true" />Connecting Gmail…</> : "Connect"}</button></article><div className="flex items-center gap-3"><span className="h-px flex-1 bg-[var(--border-subtle)]"/><span className="text-[10px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">Or configure an API</span><span className="h-px flex-1 bg-[var(--border-subtle)]"/></div><button type="button" onClick={() => { setForm(initialForm()); setErrors({}); setModal("http-create"); }} className="group w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-4 text-left transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--elevated)]"><span className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--input-bg)] text-[var(--text-secondary)]" aria-hidden="true"><svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0-18"/></svg></span><span className="min-w-0 flex-1"><span className="flex items-center justify-between gap-3"><span className="text-[14px] font-medium text-[var(--text-primary)]">HTTP API</span><span className="inline-flex h-7 shrink-0 items-center gap-1.5 rounded-[6px] border border-[var(--border-default)] px-2.5 text-[11px] font-medium text-[var(--text-primary)] transition-colors group-hover:bg-[var(--surface)]">Configure <span aria-hidden="true">→</span></span></span><span className="mt-1 block text-[12px] leading-5 text-[var(--text-secondary)]">Connect any REST API with a base URL and optional API key or bearer token.</span></span></span><span className="mt-3 flex flex-wrap gap-1.5 pl-[52px]"><span className="rounded border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--text-tertiary)]">Bearer token</span><span className="rounded border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--text-tertiary)]">API key</span><span className="rounded border border-[var(--border-subtle)] px-1.5 py-0.5 text-[10px] text-[var(--text-tertiary)]">No auth</span></span></button>{errors.api && <p role="alert" className="text-[12px] text-red-500">{errors.api}</p>}<div className="flex justify-end border-t border-[var(--border-subtle)] pt-4"><button type="button" onClick={closeModal} className={secondaryClass}>Close</button></div></div></Modal>}

    {(modal === "http-create" || modal === "edit") && <Modal title={selected ? "Edit HTTP connection" : "New HTTP connection"} description={selected ? "Update the name, endpoint, or authentication for this connection." : "Add an endpoint your workflows can call."} onClose={closeModal} wide><form onSubmit={submit} className="space-y-5"><div className="flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--elevated)] p-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] text-[var(--text-secondary)]" aria-hidden="true"><svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0-18"/></svg></span><div className="min-w-0 flex-1"><p className="text-[12px] font-medium text-[var(--text-primary)]">HTTP API</p><p className="mt-0.5 text-[11px] text-[var(--text-secondary)]">REST endpoint · reusable in your workflows</p></div><span className="rounded border border-[var(--border-subtle)] px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-[var(--text-tertiary)]">HTTP</span></div><section className="space-y-3"><div><h3 className="text-[11px] font-semibold uppercase tracking-[.12em] text-[var(--text-tertiary)]">Connection details</h3><p className="mt-1 text-[11px] text-[var(--text-secondary)]">Give this connection a clear name for your team.</p></div>
      <Field label="Connection name" htmlFor="connection-name" error={errors.name}><input id="connection-name" autoFocus value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="e.g. Shopify production" className={inputClass} /></Field></section>
      <section className="space-y-3 rounded-lg border border-[var(--border-subtle)] p-3"><div><h3 className="text-[11px] font-semibold uppercase tracking-[.12em] text-[var(--text-tertiary)]">Authentication</h3><p className="mt-1 text-[11px] text-[var(--text-secondary)]">Choose how Relay should authenticate with this API.</p></div><Field label="Authentication method" htmlFor="connection-auth"><select id="connection-auth" value={form.auth_type} onChange={(event) => changeAuth(event.target.value)} className={inputClass}>{authTypes.map((type) => <option key={type} value={type}>{authLabels[type]}</option>)}</select></Field>
      {form.auth_type !== "none" && <Field label={form.auth_type === "bearer" ? "Bearer token" : "API key"} htmlFor="connection-credential" error={errors.credential} helper={selected && !replaceCredential ? "Stored securely" : undefined}><div className="flex gap-2">{selected && !replaceCredential ? <div className={`${inputClass} flex items-center justify-between`}><span className="text-[12px] text-[var(--text-tertiary)]">Stored securely</span><button type="button" onClick={() => { setReplaceCredential(true); setForm({ ...form, credential: "" }); }} className="text-[12px] text-[var(--accent)]">Replace</button></div> : <div className="relative flex-1"><input id="connection-credential" type={credentialVisible ? "text" : "password"} autoComplete="new-password" value={form.credential} onChange={(event) => setForm({ ...form, credential: event.target.value })} placeholder="Enter credential" className={`${inputClass} pr-16`} /><button type="button" aria-label={credentialVisible ? "Hide credential" : "Show credential"} onClick={() => setCredentialVisible(!credentialVisible)} className="absolute right-2 top-1/2 -translate-y-1/2 px-1 text-[11px] text-[var(--text-tertiary)]">{credentialVisible ? "Hide" : "Show"}</button></div>}</div></Field>}
      {form.auth_type === "api_key_header" && <Field label="Header name" htmlFor="connection-header" error={errors.auth_header}><input id="connection-header" value={form.auth_header} onChange={(event) => setForm({ ...form, auth_header: event.target.value })} placeholder="X-API-Key" className={inputClass} /></Field>}
      {form.auth_type === "api_key_query" && <Field label="Query parameter name" htmlFor="connection-param" error={errors.auth_param}><input id="connection-param" value={form.auth_param} onChange={(event) => setForm({ ...form, auth_param: event.target.value })} placeholder="api_key" className={inputClass} /></Field>}
      </section><section className="space-y-3"><div><h3 className="text-[11px] font-semibold uppercase tracking-[.12em] text-[var(--text-tertiary)]">API endpoint</h3><p className="mt-1 text-[11px] text-[var(--text-secondary)]">Set the base address and an optional URL Relay can use to test connectivity.</p></div><Field label="Base URL" htmlFor="connection-base" error={errors.base_url}><input id="connection-base" type="url" value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} placeholder="https://api.example.com" className={inputClass} /></Field><div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--elevated)] p-3"><div className="flex flex-col gap-3 sm:flex-row sm:items-center"><div className="min-w-0 flex-1"><p className="text-[12px] font-medium text-[var(--text-primary)]">Test endpoint <span className="ml-1 text-[10px] font-normal text-[var(--text-tertiary)]">Optional</span></p><p className="mt-1 text-[11px] leading-4 text-[var(--text-secondary)]">Add a lightweight health-check URL if the API has one. Relay uses it only when you choose “Test connection.”</p></div>{!showTestUrl && <button type="button" onClick={() => setShowTestUrl(true)} className={secondaryClass}>＋ Add test URL</button>}{showTestUrl && <button type="button" onClick={() => { setForm((current) => ({ ...current, test_url: "" })); setErrors((current) => ({ ...current, test_url: undefined })); setShowTestUrl(false); }} className="text-[12px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">Remove</button>}</div>{showTestUrl && <div className="mt-3"><Field label="Test URL" htmlFor="connection-test" error={errors.test_url}><input id="connection-test" type="url" value={form.test_url} onChange={(event) => setForm({ ...form, test_url: event.target.value })} placeholder="https://api.example.com/health" className={inputClass} /></Field></div>}</div></section>{errors.api && <p role="alert" className="rounded border border-red-500/30 bg-red-500/5 p-2.5 text-[12px] text-red-500">{errors.api}</p>}
      <div className="flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4"><button type="button" onClick={closeModal} className={secondaryClass}>Cancel</button><button type="submit" disabled={saving} className={primaryClass}>{saving ? "Saving…" : selected ? "Save connection" : "Create connection"}</button></div>
    </form></Modal>}

    {modal === "details" && selected && selected.provider === "gmail" && <div className="connection-overlay fixed inset-0 z-[100] bg-black/50" onMouseDown={(event) => event.target === event.currentTarget && closeModal()}><aside role="dialog" aria-modal="true" aria-labelledby="connection-detail-title" className="connection-drawer absolute inset-y-0 right-0 flex w-full max-w-[520px] flex-col border-l border-[var(--border-default)] bg-[var(--surface)]"><header className="border-b border-[var(--border-subtle)] p-5"><div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--text-tertiary)]">Connected account</p><h2 id="connection-detail-title" className="mt-2 text-[20px] font-semibold tracking-tight">Gmail</h2></div><button type="button" onClick={closeModal} aria-label="Close details" className="rounded-[6px] border border-[var(--border-subtle)] px-2 py-1 text-[18px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)]">×</button></div><div className="mt-5 flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--elevated)] p-3"><div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)]"><GmailIcon className="h-6 w-6" /></div><div className="min-w-0 flex-1"><p className="truncate text-[13px] font-medium text-[var(--text-primary)]">{selected.config?.email || selected.name}</p><p className="mt-1 text-[11px] text-[var(--text-secondary)]">Gmail account</p></div><span className="inline-flex shrink-0 items-center gap-1.5 text-[11px] text-[var(--text-secondary)]"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true"/>Connected</span></div></header><div className="flex-1 space-y-6 overflow-y-auto p-5"><section><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Connection details</h3><div className="divide-y divide-[var(--border-subtle)] rounded-md border border-[var(--border-subtle)] px-3">{[["Service", "Gmail"], ["Account", selected.config?.email || "—"], ["Sign-in method", "Google OAuth"], ["Connected", selected.created_at ? new Date(selected.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "—"]].map(([label, value]) => <div key={label} className="flex justify-between gap-4 py-3 text-[12px]"><span className="text-[var(--text-tertiary)]">{label}</span><span className="max-w-[65%] break-all text-right text-[var(--text-secondary)]">{value}</span></div>)}</div></section><section className="rounded-md border border-[var(--border-subtle)] p-3"><h3 className="text-[12px] font-medium text-[var(--text-primary)]">Used by workflows</h3><p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">Workflows can use this account when sending email with Gmail.</p></section>{errors.api && <p role="alert" className="text-[12px] text-red-500">{errors.api}</p>}</div><footer className="border-t border-[var(--border-subtle)] p-5"><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Manage connection</h3><div className="grid gap-2"><button type="button" onClick={() => { setErrors({}); setModal("delete"); }} className={`${buttonClass} justify-start border-red-500/30 text-red-500 hover:bg-red-500/5`}>Disconnect Gmail</button></div><p className="mt-3 truncate font-mono text-[10px] text-[var(--text-disabled)]">ID · {selected.id}</p></footer></aside></div>}

    {modal === "details" && selected && selected.provider !== "gmail" && <div className="connection-overlay fixed inset-0 z-[100] bg-black/50" onMouseDown={(event) => event.target === event.currentTarget && closeModal()}><aside role="dialog" aria-modal="true" aria-labelledby="connection-detail-title" className="connection-drawer absolute inset-y-0 right-0 flex w-full max-w-[520px] flex-col border-l border-[var(--border-default)] bg-[var(--surface)]"><header className="flex items-start justify-between border-b border-[var(--border-subtle)] p-5"><div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--text-tertiary)]">HTTP API connection</p><h2 id="connection-detail-title" className="mt-2 truncate text-[20px] font-semibold tracking-tight">{selected.name}</h2><div className="mt-2 flex items-center gap-2 text-[12px] text-[var(--text-secondary)]"><span className="font-mono">HTTP</span><span className="text-[var(--text-disabled)]">·</span>{authLabels[selected.auth_type] || selected.auth_type}</div></div><button type="button" onClick={closeModal} aria-label="Close details" className="rounded-[6px] border border-[var(--border-subtle)] px-2 py-1 text-[18px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)]">×</button></header><div className="flex-1 space-y-6 overflow-y-auto p-5"><section><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Endpoints</h3><div className="divide-y divide-[var(--border-subtle)] rounded-md border border-[var(--border-subtle)] px-3">{[["Base URL", selected.config?.base_url || "—"], ["Test URL", selected.config?.test_url || "Not configured"]].map(([label, value]) => <div key={label} className="py-3"><span className="block text-[11px] text-[var(--text-tertiary)]">{label}</span><code className="mt-1 block break-all font-mono text-[12px] leading-5 text-[var(--text-secondary)]">{value}</code></div>)}</div></section><section><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Configuration</h3><div className="divide-y divide-[var(--border-subtle)] rounded-md border border-[var(--border-subtle)] px-3">{[["Provider", "HTTP"], ["Authentication", authLabels[selected.auth_type] || selected.auth_type], ...(selected.auth_type === "api_key_header" ? [["Header name", selected.config?.auth_header || "—"]] : []), ...(selected.auth_type === "api_key_query" ? [["Query parameter", selected.config?.auth_param || "—"]] : []), ["Created", selected.created_at ? new Date(selected.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "—"]].map(([label, value]) => <div key={label} className="flex justify-between gap-4 py-3 text-[12px]"><span className="text-[var(--text-tertiary)]">{label}</span><span className="max-w-[65%] break-all text-right text-[var(--text-secondary)]">{value}</span></div>)}</div><p className="mt-2 text-[11px] text-[var(--text-tertiary)]">Credentials are stored securely and are never displayed.</p></section>{testResult && testResult.connectionId === selected.id && <section aria-live="polite"><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Last connection test</h3><div className={`rounded-md border p-3 ${testResult.success ? "border-emerald-500/30 bg-emerald-500/[0.04]" : "border-red-500/30 bg-red-500/[0.04]"}`}><div className="flex items-start justify-between gap-3"><p className="text-[13px] font-medium">{testResult.success ? "Connection test successful" : "Connection test failed"}</p>{testResult.statusCode != null && <span className="shrink-0 rounded border border-[var(--border-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]">{testResult.statusCode}</span>}</div><p className="mt-1 text-[12px] text-[var(--text-secondary)]">{testResult.message || "Connection test completed."}</p>{testResult.response !== undefined && testResult.response !== null && <div className="mt-3 border-t border-[var(--border-subtle)] pt-3"><h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Response payload</h4><pre className="max-h-64 max-w-full overflow-auto whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded border border-[var(--border-subtle)] bg-[var(--input-bg)] p-2 font-mono text-[11px] leading-5 text-[var(--text-secondary)]">{safeResponse(testResult.response)}</pre></div>}</div></section>}<section className="border-t border-[var(--border-subtle)] pt-4"><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Manage connection</h3><div className="grid grid-cols-2 gap-2"><button type="button" onClick={() => openEdit(selected)} className={secondaryClass}>Edit connection</button>{selected.config?.test_url ? <button type="button" onClick={() => runTest(selected)} disabled={testingId === selected.id} className={secondaryClass}>{testingId === selected.id ? "Testing…" : "Test connection"}</button> : <button type="button" onClick={() => { setTestResult(null); openEdit(selected); setShowTestUrl(true); }} className={secondaryClass}>Add test URL</button>}<button type="button" onClick={() => { setErrors({}); setModal("delete"); }} className={`${buttonClass} border-red-500/30 text-red-500 hover:bg-red-500/5`}>Delete connection</button></div>{errors.api && <p role="alert" className="mt-3 text-[12px] text-red-500">{errors.api}</p>}</section></div><footer className="border-t border-[var(--border-subtle)] p-4"><p className="truncate font-mono text-[10px] text-[var(--text-disabled)]">ID · {selected.id}</p></footer></aside></div>}

    {modal === "delete" && selected && <Modal title="Delete connection?" onClose={closeModal}><p className="text-[13px] leading-5 text-[var(--text-secondary)]">This will permanently remove <strong className="text-[var(--text-primary)]">{selected.name}</strong>. Workflows using it may no longer be able to execute their HTTP actions.</p>{errors.api && <p role="alert" className="mt-3 text-[12px] text-red-500">{errors.api}</p>}<div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4"><button type="button" onClick={closeModal} className={secondaryClass}>Cancel</button><button type="button" disabled={deleting} onClick={remove} className={`${buttonClass} border-red-500/40 bg-red-600 text-white hover:bg-red-700`}>{deleting ? "Deleting…" : "Delete connection"}</button></div></Modal>}

    {modal === "test" && testResult && <Modal title={testResult.success ? "Connection test successful" : "Connection test failed"} onClose={closeModal} wide><div className="space-y-4"><div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3"><span className="text-[12px] text-[var(--text-secondary)]">Status</span><span className={`font-mono text-[13px] ${testResult.success ? "text-[var(--text-primary)]" : "text-red-500"}`}>{testResult.statusCode ?? "Unavailable"}</span></div><p className="text-[12px] text-[var(--text-secondary)]">{testResult.message || "Connection test completed."}</p>{testResult.response !== undefined && testResult.response !== null && <div><h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Response</h3><pre className="max-w-full overflow-x-hidden whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded-md border border-[var(--border-subtle)] bg-[var(--input-bg)] p-3 font-mono text-[11px] leading-5 text-[var(--text-secondary)]">{safeResponse(testResult.response)}</pre></div>}<div className="flex justify-end border-t border-[var(--border-subtle)] pt-4">{!testResult.success && selected && <button type="button" onClick={() => runTest(selected)} className={`${secondaryClass} mr-auto`}>Retry</button>}<button type="button" onClick={closeModal} className={secondaryClass}>Close</button></div></div></Modal>}
  </div><style jsx global>{`@keyframes connection-fade-in { from { opacity: 0; } to { opacity: 1; } } @keyframes connection-dialog-in { from { opacity: 0; transform: translateY(8px) scale(.99); } to { opacity: 1; transform: translateY(0) scale(1); } } @keyframes connection-drawer-in { from { opacity: .7; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } } @keyframes connection-toast-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } } .connection-overlay { animation: connection-fade-in 140ms ease-out both; } .connection-dialog { animation: connection-dialog-in 180ms ease-out both; } .connection-drawer { animation: connection-drawer-in 180ms ease-out both; } .connection-toast { animation: connection-toast-in 200ms ease-out both; } .connection-result { animation: connection-dialog-in 180ms ease-out both; } @media (prefers-reduced-motion: reduce) { .connection-overlay, .connection-dialog, .connection-drawer, .connection-toast, .connection-result { animation: none; } }`}</style></DashboardShell></ProtectedRoute>;
}
