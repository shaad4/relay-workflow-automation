"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import { ExecutionIcon, RefreshExecutions } from "@/components/dashboard/ExecutionUI";
import Pagination from "@/components/Pagination";
import { useAuth } from "@/context/AuthContext";
import { approveApproval, getApproval, getApprovals, rejectApproval } from "@/services/approvals";

const buttonBase = "inline-flex h-9 items-center justify-center gap-1.5 rounded-[6px] border px-3 text-[12px] font-medium transition-colors duration-100 disabled:cursor-not-allowed disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/40";
const secondaryButton = `${buttonBase} border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--elevated)]`;
const primaryButton = `${buttonBase} border-transparent bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]`;
const rejectButton = `${buttonBase} border-red-500/30 bg-red-500/5 text-red-500 hover:bg-red-500/10 focus-visible:ring-red-500/30`;
const PAGE_SIZE = 10;

function CheckCircleIcon({ className = "h-5 w-5", ...props }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className} aria-hidden="true" {...props}><circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16.5 9"/></svg>;
}

function ClockIcon({ className = "h-5 w-5", ...props }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={className} aria-hidden="true" {...props}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
}

function formatRequested(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time unavailable";
  const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} ${minutes === 1 ? "minute" : "minutes"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ${hours === 1 ? "hour" : "hours"} ago`;
  if (hours < 48) return "Yesterday";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}

function formatDateTime(value) {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not set";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function StatusBadge({ status = "pending" }) {
  const normalized = String(status).toLowerCase();
  const styles = {
    pending: "border-amber-500/30 bg-amber-500/5 text-amber-700 dark:text-amber-300",
    approved: "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
    rejected: "border-red-500/30 bg-red-500/5 text-red-600 dark:text-red-400",
  };
  const label = normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : "Unknown";
  return <span className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 text-[10px] font-medium ${styles[normalized] || "border-[var(--border-subtle)] bg-[var(--elevated)] text-[var(--text-secondary)]"}`}><span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true"/>{label}</span>;
}

function ApprovalMessage({ message }) {
  return String(message || "Approval request").split(/(\{\{[^{}]+\}\})/g).map((part, index) => part.startsWith("{{") && part.endsWith("}}")
    ? <code key={index} className="rounded bg-[var(--elevated)] px-1 py-0.5 font-mono text-[12px] font-normal text-[var(--text-secondary)]">{part}</code>
    : <span key={index}>{part}</span>);
}

function ApprovalSkeleton() {
  return <div aria-label="Loading approvals" role="status" className="space-y-3"><span className="sr-only">Loading approvals</span>{[0, 1, 2].map((row) => <div key={row} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 sm:p-5"><div className="flex items-start gap-3"><div className="h-10 w-10 animate-pulse rounded-lg bg-[var(--elevated)]"/><div className="min-w-0 flex-1 space-y-3"><div className="h-4 w-28 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-5 w-3/4 animate-pulse rounded bg-[var(--elevated)]"/></div><div className="h-6 w-20 animate-pulse rounded bg-[var(--elevated)]"/></div><div className="mt-4 flex justify-between border-t border-[var(--border-subtle)] pt-4"><div className="h-3 w-48 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-9 w-52 animate-pulse rounded bg-[var(--elevated)]"/></div></div>)}</div>;
}

function ConfirmDecisionDialog({ decision, busy, onCancel, onConfirm }) {
  const cancelRef = useRef(null);
  const confirmRef = useRef(null);
  const isApprove = decision?.action === "approve";
  useEffect(() => {
    if (!decision) return undefined;
    const previousFocus = document.activeElement;
    cancelRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === "Escape" && !busy) { event.preventDefault(); onCancel(); }
      if (event.key === "Tab") {
        const first = cancelRef.current;
        const last = confirmRef.current;
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => { window.removeEventListener("keydown", onKeyDown); previousFocus?.focus?.(); };
  }, [decision, busy, onCancel]);
  if (!decision) return null;
  return <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/55 p-4" onMouseDown={(event) => event.target === event.currentTarget && !busy && onCancel()}><section role="alertdialog" aria-modal="true" aria-labelledby="approval-decision-title" aria-describedby="approval-decision-description" className="w-full max-w-md rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-2xl"><div className="mb-4 flex items-start gap-3"><div className={`grid h-9 w-9 shrink-0 place-items-center rounded-md border ${isApprove ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400" : "border-red-500/30 bg-red-500/5 text-red-500"}`}><CheckCircleIcon className="h-5 w-5"/></div><div><h2 id="approval-decision-title" className="text-[16px] font-semibold text-[var(--text-primary)]">{isApprove ? "Approve this request?" : "Reject this request?"}</h2><p id="approval-decision-description" className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">{isApprove ? "The workflow will continue along the approved branch." : "The workflow will continue along the rejected branch, or finish if no branch is configured."}</p></div></div><p className="mb-5 line-clamp-3 rounded-md border border-[var(--border-subtle)] bg-[var(--elevated)] p-3 text-[12px] leading-5 text-[var(--text-secondary)]"><ApprovalMessage message={decision.approval?.message}/></p><div className="flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4"><button ref={cancelRef} type="button" disabled={busy} onClick={onCancel} className={secondaryButton}>Cancel</button><button ref={confirmRef} type="button" disabled={busy} onClick={onConfirm} className={isApprove ? primaryButton : `${buttonBase} border-transparent bg-red-600 text-white hover:bg-red-700`}>{busy ? "Processing…" : isApprove ? "Approve" : "Reject"}</button></div></section></div>;
}

export default function ApprovalsPage() {
  const { isInitializing } = useAuth();
  const [status, setStatus] = useState("pending");
  const [approvals, setApprovals] = useState([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [reload, setReload] = useState(0);
  const [selectedApproval, setSelectedApproval] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [decision, setDecision] = useState(null);
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const closeDetailRef = useRef(null);

  const refresh = useCallback(() => setReload((value) => value + 1), []);
  const notify = useCallback((message, kind = "success") => setNotice({ message, kind, key: Date.now() }), []);

  useEffect(() => { document.title = "Approvals | Relay"; }, []);
  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(() => setNotice(null), 3500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    if (isInitializing) return undefined;
    let active = true;
    setLoading(true);
    setLoadError(false);
    getApprovals(status).then((response) => {
      if (!active) return;
      setApprovals((Array.isArray(response) ? response : response?.approvals || []).filter(approval => approval.status === status));
    }).catch(() => {
      if (active) setLoadError(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [isInitializing, reload, status]);

  useEffect(() => {
    const onUpdated = () => { setSelectedApproval(null); setDecision(null); refresh(); };
    window.addEventListener("relay:approvals-updated", onUpdated);
    window.addEventListener("focus", onUpdated);
    return () => {
      window.removeEventListener("relay:approvals-updated", onUpdated);
      window.removeEventListener("focus", onUpdated);
    };
  }, [refresh]);

  useEffect(() => {
    if (!selectedApproval) return undefined;
    const onKeyDown = (event) => { if (event.key === "Escape" && !decision) setSelectedApproval(null); };
    window.addEventListener("keydown", onKeyDown);
    closeDetailRef.current?.focus();
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedApproval?.id, decision]);

  const showDetails = async (approval) => {
    setSelectedApproval(approval);
    setDetailLoading(true);
    setDetailError("");
    try {
      const response = await getApproval(approval.id);
      setSelectedApproval(response?.approval || response);
    } catch (error) {
      if (error.status === 404) {
        setDetailError("This approval is no longer available.");
        refresh();
      } else {
        setDetailError("Unable to load approval details. Try again.");
      }
    } finally {
      setDetailLoading(false);
    }
  };

  const retryDetails = () => selectedApproval && showDetails(selectedApproval);
  const startDecision = (approval, action) => setDecision({ approval, action });
  const closeDecision = useCallback(() => { if (!decisionBusy) setDecision(null); }, [decisionBusy]);
  const pageCount = Math.max(1, Math.ceil(approvals.length / PAGE_SIZE));
  const paginatedApprovals = approvals.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => { setPage((current) => Math.min(current, pageCount)); }, [pageCount]);

  const confirmDecision = async () => {
    if (!decision || decisionBusy) return;
    setDecisionBusy(true);
    const { approval, action } = decision;
    try {
      if (action === "approve") await approveApproval(approval.id);
      else await rejectApproval(approval.id);
      window.dispatchEvent(new Event("relay:approvals-updated"));
      setApprovals((current) => current.filter((item) => item.id !== approval.id));
      setSelectedApproval((current) => current?.id === approval.id ? null : current);
      setDecision(null);
      notify(action === "approve" ? "Approval recorded. The workflow will continue." : "Rejection recorded. The workflow will follow its rejection path.");
      refresh();
    } catch (error) {
      if (error.status === 409) {
        window.dispatchEvent(new Event("relay:approvals-updated"));
        setDecision(null);
        setSelectedApproval((current) => current?.id === approval.id ? null : current);
        notify("This approval was already handled. The inbox has been refreshed.", "info");
        refresh();
      } else if (error.status === 404) {
        window.dispatchEvent(new Event("relay:approvals-updated"));
        setDecision(null);
        setSelectedApproval((current) => current?.id === approval.id ? null : current);
        notify("This approval is no longer available. The inbox has been refreshed.", "error");
        refresh();
      } else if (error.status === 422) {
        notify("This approval request could not be processed.", "error");
      } else {
        notify("Unable to submit your decision. Please try again.", "error");
      }
    } finally {
      setDecisionBusy(false);
    }
  };

  const content = <div className="execution-workspace">
    <header className="execution-page-header">
      <div className="execution-heading-group">
        <span className="execution-page-icon"><CheckCircleIcon className="h-6 w-6"/></span>
        <div><p className="execution-eyebrow">Human decisions · Workflow automation</p><h1>Approval Inbox</h1><p className="execution-header-description">A moment for your judgment. Review the request, then choose what happens next.</p></div>
      </div>
      <RefreshExecutions busy={loading} onRefresh={refresh}/>
    </header>

    {notice && <div key={notice.key} role={notice.kind === "error" ? "alert" : "status"} className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2.5 text-[12px] ${notice.kind === "success" ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300" : notice.kind === "error" ? "border-red-500/30 bg-red-500/5 text-red-600 dark:text-red-400" : "border-[var(--border-default)] bg-[var(--elevated)] text-[var(--text-secondary)]"}`}><span>{notice.message}</span><button type="button" onClick={() => setNotice(null)} aria-label="Dismiss notification" className="shrink-0 text-current opacity-70 hover:opacity-100">×</button></div>}

    <section className="overflow-hidden rounded-[10px] border border-[var(--border-subtle)] bg-[var(--surface)]" aria-label="Approval inbox">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)] px-4 pt-2 sm:px-6">
        <nav aria-label="Approval views" className="flex gap-5">{["pending", "cancelled"].map(value => <button key={value} type="button" aria-pressed={status === value} className={`inline-flex min-h-12 items-center gap-2 border-b-2 px-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] ${status === value ? "border-[var(--accent)] text-[var(--text-primary)]" : "border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)]"}`} onClick={() => { if (value === status) return; setStatus(value); setPage(1); setLoading(true); setSelectedApproval(null); setDecision(null); }}>
          {value === "pending" ? <ClockIcon className="h-3.5 w-3.5"/> : <ExecutionIcon type="history" className="h-3.5 w-3.5"/>}{value === "pending" ? "Pending" : "Cancelled"}
          {status === value && !loading && !loadError && <span className="min-w-5 rounded border border-[var(--border-subtle)] bg-[var(--elevated)] px-1.5 py-0.5 text-center font-mono text-[10px] tabular-nums">{approvals.length}</span>}
        </button>)}</nav>
        <span className="mb-2 hidden items-center gap-1.5 text-[11px] text-[var(--text-tertiary)] sm:inline-flex"><ExecutionIcon type={status === "pending" ? "clock" : "history"} className="h-3.5 w-3.5"/>{status === "pending" ? "Assigned to you" : "Read-only history"}</span>
      </div>

      <div className="flex items-center justify-between gap-6 border-b border-[var(--border-subtle)] bg-[var(--canvas)] px-5 py-5 sm:px-6">
        <div><h2 className="text-sm font-semibold tracking-tight">{status === "pending" ? "Your next decisions" : "Requests that came to a stop"}</h2><p className="mt-1.5 text-xs leading-5 text-[var(--text-secondary)]">{status === "pending" ? "These workflows are waiting for a human decision." : "Cancelled requests stay here for reference. No decision is needed."}</p></div>
        <div className="hidden shrink-0 border-l border-[var(--border-subtle)] pl-6 text-right sm:block"><span className="font-mono text-2xl font-medium tabular-nums tracking-tight">{loading || loadError ? "—" : String(approvals.length).padStart(2, "0")}</span><p className="mt-1 text-[10px] text-[var(--text-tertiary)]">{status === "pending" ? "awaiting review" : "cancelled requests"}</p></div>
      </div>

      {loading && <div className="p-4 sm:p-6"><ApprovalSkeleton/></div>}
      {loadError && !loading && <div className="px-6 py-16 text-center"><ExecutionIcon type="alert" className="mx-auto mb-4 h-6 w-6 text-[var(--text-secondary)]"/><h3 className="text-sm font-semibold">Unable to load approvals.</h3><p className="mt-2 text-xs text-[var(--text-secondary)]">We couldn’t retrieve your approvals. Try again.</p><button type="button" onClick={refresh} className={`${secondaryButton} mt-5`}>Retry</button></div>}
      {!loading && !loadError && approvals.length === 0 && <div className="px-6 py-16 text-center sm:py-24">
        <div aria-hidden="true" className="mx-auto mb-6 flex w-fit items-center gap-2 text-[var(--text-tertiary)]"><span className="h-px w-8 bg-[var(--border-default)]"/><span className="grid h-14 w-14 place-items-center rounded-xl border border-[var(--border-default)] bg-[var(--canvas)] shadow-sm">{status === "pending" ? <CheckCircleIcon className="h-6 w-6"/> : <ExecutionIcon type="history" className="h-6 w-6"/>}</span><span className="h-px w-8 bg-[var(--border-default)]"/></div>
        <h3 className="text-base font-semibold tracking-tight">{status === "pending" ? "You’re all caught up" : "Nothing cancelled"}</h3><p className="mx-auto mt-2 max-w-sm text-xs leading-6 text-[var(--text-secondary)]">{status === "pending" ? "No approvals are waiting for your decision." : "No cancelled approvals yet."}</p>
        <span className="mt-6 inline-block rounded border border-[var(--border-subtle)] px-2.5 py-1.5 text-[10px] text-[var(--text-tertiary)]">{status === "pending" ? "New requests will appear here" : "Your approval history stays in one place"}</span>
      </div>}
      {!loading && !loadError && approvals.length > 0 && <>
        <div className="divide-y divide-[var(--border-subtle)]">{paginatedApprovals.map((approval, index) => <article key={approval.id} className="group px-4 py-5 transition-colors hover:bg-[var(--canvas)] sm:px-6 sm:py-6">
          <div className="flex gap-3 sm:gap-5">
            <div className="hidden w-9 shrink-0 flex-col items-center gap-3 sm:flex" aria-hidden="true"><span className="font-mono text-[10px] tabular-nums text-[var(--text-tertiary)]">{String((page - 1) * PAGE_SIZE + index + 1).padStart(2, "0")}</span><span className={`grid h-9 w-9 place-items-center rounded-lg border ${approval.status === "pending" ? "border-[var(--border-default)] bg-[var(--canvas)] text-[var(--text-secondary)]" : "border-[var(--border-subtle)] text-[var(--text-tertiary)]"}`}>{approval.status === "pending" ? <ClockIcon className="h-4 w-4"/> : <ExecutionIcon type="history" className="h-4 w-4"/>}</span></div>
            <div className="min-w-0 flex-1">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><span className="font-mono text-[10px] text-[var(--text-tertiary)]" title={approval.execution_id}>RUN / {String(approval.execution_id || "").slice(0, 8) || "Unavailable"}</span><StatusBadge status={approval.status}/></div>
              <button type="button" onClick={() => showDetails(approval)} className="block w-full rounded text-left text-[14px] font-medium leading-6 text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--accent)] sm:text-[15px]"><span className="line-clamp-3 break-words [overflow-wrap:anywhere]"><ApprovalMessage message={approval.message}/></span><span className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-normal text-[var(--text-tertiary)] group-hover:text-[var(--text-secondary)]">View request <span aria-hidden="true">↗</span></span></button>
              <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-[var(--border-subtle)] pt-4">
                <time dateTime={approval.created_at} title={formatDateTime(approval.created_at)} className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-tertiary)]"><ClockIcon className="h-3.5 w-3.5"/>Requested {formatRequested(approval.created_at)}</time>
                {approval.status === "pending" ? <div className="flex gap-2"><button type="button" onClick={() => startDecision(approval, "reject")} className={secondaryButton}>Reject</button><button type="button" onClick={() => startDecision(approval, "approve")} className={primaryButton}><CheckCircleIcon className="h-3.5 w-3.5"/>Approve</button></div> : <span className="text-[11px] text-[var(--text-tertiary)]">No action required</span>}
              </div>
            </div>
          </div>
        </article>)}</div>
        <div className="border-t border-[var(--border-subtle)] bg-[var(--canvas)] px-4 py-3 sm:px-6"><Pagination page={page} pageSize={PAGE_SIZE} total={approvals.length} onPageChange={setPage}/></div>
      </>}
    </section>
    <p className="flex items-start gap-2 text-[11px] leading-5 text-[var(--text-tertiary)]"><ExecutionIcon type="generic" className="mt-0.5 h-3.5 w-3.5 shrink-0"/>{status === "pending" ? "Each decision continues a workflow along its configured approval or rejection path." : "Cancelling a workflow preserves its approval records and completed steps."}</p>
  </div>;

  return <ProtectedRoute><DashboardShell pageTitle="Approvals">{content}
    {selectedApproval && <div className="fixed inset-0 z-[100] bg-black/50" onMouseDown={(event) => event.target === event.currentTarget && setSelectedApproval(null)}><aside role="dialog" aria-modal="true" aria-labelledby="approval-details-title" className="absolute inset-y-0 right-0 flex w-full max-w-[520px] flex-col border-l border-[var(--border-default)] bg-[var(--surface)] shadow-2xl"><div className="flex items-start justify-between border-b border-[var(--border-subtle)] p-5"><div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--text-tertiary)]">Approval request</p><h2 id="approval-details-title" className="mt-2 text-[19px] font-semibold tracking-tight text-[var(--text-primary)]">Details</h2><div className="mt-2"><StatusBadge status={selectedApproval.status}/></div></div><button ref={closeDetailRef} type="button" onClick={() => setSelectedApproval(null)} aria-label="Close approval details" className="rounded-[6px] border border-[var(--border-subtle)] px-2 py-1 text-[18px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/40">×</button></div><div className="flex-1 space-y-6 overflow-y-auto p-5">{detailLoading ? <div role="status" className="space-y-4"><span className="sr-only">Loading approval details</span><div className="h-20 animate-pulse rounded-md bg-[var(--elevated)]"/><div className="h-4 w-1/2 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-4 w-3/4 animate-pulse rounded bg-[var(--elevated)]"/></div> : detailError ? <div className="rounded-md border border-red-500/30 bg-red-500/5 p-4"><p role="alert" className="text-[12px] text-red-600 dark:text-red-400">{detailError}</p>{!detailError.includes("no longer") && <button type="button" onClick={retryDetails} className="mt-3 text-[12px] font-medium text-[var(--accent)] hover:underline">Retry</button>}</div> : <><section><h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Approval message</h3><p className="whitespace-pre-wrap rounded-md border border-[var(--border-subtle)] bg-[var(--elevated)] p-4 text-[13px] leading-6 text-[var(--text-primary)]"><ApprovalMessage message={selectedApproval.message || "No message provided."}/></p></section><section><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Request details</h3><dl className="divide-y divide-[var(--border-subtle)] rounded-md border border-[var(--border-subtle)] px-3">{[["Requested", formatDateTime(selectedApproval.created_at)], ["Execution ID", selectedApproval.execution_id], ["Approval ID", selectedApproval.id], ...(selectedApproval.timeout_at ? [["Deadline", formatDateTime(selectedApproval.timeout_at)]] : [])].map(([label, value]) => <div key={label} className="flex flex-col gap-1 py-3 sm:flex-row sm:justify-between sm:gap-4"><dt className="text-[11px] text-[var(--text-tertiary)]">{label}</dt><dd className={`break-all text-[12px] text-[var(--text-secondary)] ${label.endsWith("ID") ? "font-mono" : "sm:text-right"}`}>{value || "Unavailable"}</dd></div>)}</dl></section></>}</div>{!detailLoading && !detailError && String(selectedApproval.status).toLowerCase() === "pending" && <div className="grid grid-cols-2 gap-2 border-t border-[var(--border-subtle)] p-4"><button type="button" onClick={() => startDecision(selectedApproval, "reject")} className={rejectButton}>Reject</button><button type="button" onClick={() => startDecision(selectedApproval, "approve")} className={primaryButton}>Approve</button></div>}</aside></div>}
    <ConfirmDecisionDialog decision={decision} busy={decisionBusy} onCancel={closeDecision} onConfirm={confirmDecision}/>
  </DashboardShell></ProtectedRoute>;
}
