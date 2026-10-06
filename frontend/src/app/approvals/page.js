"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
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
  return <div aria-label="Loading approvals" role="status" className="space-y-3"><span className="sr-only">Loading pending approvals</span>{[0, 1, 2].map((row) => <div key={row} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 sm:p-5"><div className="flex items-start gap-3"><div className="h-10 w-10 animate-pulse rounded-lg bg-[var(--elevated)]"/><div className="min-w-0 flex-1 space-y-3"><div className="h-4 w-28 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-5 w-3/4 animate-pulse rounded bg-[var(--elevated)]"/></div><div className="h-6 w-20 animate-pulse rounded bg-[var(--elevated)]"/></div><div className="mt-4 flex justify-between border-t border-[var(--border-subtle)] pt-4"><div className="h-3 w-48 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-9 w-52 animate-pulse rounded bg-[var(--elevated)]"/></div></div>)}</div>;
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
  return <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/55 p-4" onMouseDown={(event) => event.target === event.currentTarget && !busy && onCancel()}><section role="alertdialog" aria-modal="true" aria-labelledby="approval-decision-title" aria-describedby="approval-decision-description" className="w-full max-w-md rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-5 shadow-2xl"><div className="mb-4 flex items-start gap-3"><div className={`grid h-9 w-9 shrink-0 place-items-center rounded-md border ${isApprove ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400" : "border-red-500/30 bg-red-500/5 text-red-500"}`}><CheckCircleIcon className="h-5 w-5"/></div><div><h2 id="approval-decision-title" className="text-[16px] font-semibold text-[var(--text-primary)]">{isApprove ? "Approve this request?" : "Reject this request?"}</h2><p id="approval-decision-description" className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">{isApprove ? "The workflow will continue after this approval." : "Rejecting this request will stop the workflow execution."}</p></div></div><p className="mb-5 line-clamp-3 rounded-md border border-[var(--border-subtle)] bg-[var(--elevated)] p-3 text-[12px] leading-5 text-[var(--text-secondary)]"><ApprovalMessage message={decision.approval?.message}/></p><div className="flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4"><button ref={cancelRef} type="button" disabled={busy} onClick={onCancel} className={secondaryButton}>Cancel</button><button ref={confirmRef} type="button" disabled={busy} onClick={onConfirm} className={isApprove ? primaryButton : `${buttonBase} border-transparent bg-red-600 text-white hover:bg-red-700`}>{busy ? "Processing…" : isApprove ? "Approve" : "Reject"}</button></div></section></div>;
}

export default function ApprovalsPage() {
  const { isInitializing } = useAuth();
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
    getApprovals().then((response) => {
      if (!active) return;
      setApprovals(Array.isArray(response) ? response : response?.approvals || []);
    }).catch(() => {
      if (active) setLoadError(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [isInitializing, reload]);

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
      notify(action === "approve" ? "Approval approved. The workflow has resumed." : "Approval rejected. The workflow has been stopped.");
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

  const content = <div className="w-full space-y-6">
    <header className="flex flex-col gap-4 border-b border-[var(--border-subtle)] pb-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="mb-2 text-[11px] font-medium uppercase tracking-[.16em] text-[var(--text-tertiary)]">Workflow tasks</p><h1 className="text-[26px] font-semibold leading-[32px] tracking-tight text-[var(--text-primary)]">Approvals</h1><p className="mt-1 text-[13px] text-[var(--text-secondary)]">Review and respond to workflow actions that require your approval.</p></div><button type="button" onClick={refresh} disabled={loading} className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] px-3 text-[12px] font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--elevated)] disabled:opacity-50"><span aria-hidden="true">↻</span>Refresh</button></header>

    {notice && <div key={notice.key} role={notice.kind === "error" ? "alert" : "status"} className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2.5 text-[12px] ${notice.kind === "success" ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300" : notice.kind === "error" ? "border-red-500/30 bg-red-500/5 text-red-600 dark:text-red-400" : "border-[var(--border-default)] bg-[var(--elevated)] text-[var(--text-secondary)]"}`}><span>{notice.message}</span><button type="button" onClick={() => setNotice(null)} aria-label="Dismiss notification" className="shrink-0 text-current opacity-70 hover:opacity-100">×</button></div>}

    {loading && <ApprovalSkeleton/>}
    {loadError && !loading && <section className="rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] p-8 text-center"><h2 className="text-[14px] font-semibold text-[var(--text-primary)]">Unable to load approvals.</h2><p className="mt-1 text-[13px] text-[var(--text-secondary)]">We couldn’t retrieve your pending approvals. Try again.</p><button type="button" onClick={refresh} className={`${secondaryButton} mt-4`}>Retry</button></section>}
    {!loading && !loadError && approvals.length === 0 && <section className="rounded-xl border border-dashed border-[var(--border-default)] bg-[var(--surface)] px-6 py-16 text-center"><div className="mx-auto mb-4 grid h-11 w-11 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--elevated)] text-[var(--text-secondary)]"><CheckCircleIcon className="h-6 w-6"/></div><h2 className="text-[16px] font-semibold text-[var(--text-primary)]">No pending approvals</h2><p className="mx-auto mt-2 max-w-sm text-[13px] leading-5 text-[var(--text-secondary)]">You’re all caught up. Workflow approvals that need your attention will appear here.</p></section>}
    {!loading && !loadError && approvals.length > 0 && <div className="space-y-3"><section aria-label="Pending approvals" className="space-y-3"><div className="flex items-center justify-between"><h2 className="text-[13px] font-semibold text-[var(--text-primary)]">Pending requests</h2><span className="rounded-full border border-[var(--border-subtle)] bg-[var(--surface)] px-2.5 py-1 text-[10px] font-medium text-[var(--text-secondary)]">{approvals.length} {approvals.length === 1 ? "request" : "requests"}</span></div>{paginatedApprovals.map((approval) => <article key={approval.id} role="button" tabIndex={0} aria-label={`View approval: ${approval.message || "Approval request"}`} onClick={() => showDetails(approval)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); showDetails(approval); } }} className="cursor-pointer rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--elevated)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/40 sm:p-5"><div className="flex items-start gap-3 sm:gap-4"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--elevated)] text-[var(--text-secondary)]"><ClockIcon className="h-[18px] w-[18px]"/></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-[10px] font-semibold uppercase tracking-[.12em] text-[var(--text-tertiary)]">Approval request</p><StatusBadge status={approval.status}/></div><p className="mt-1.5 break-words text-left text-[14px] font-medium leading-6 text-[var(--text-primary)] sm:text-[15px]"><ApprovalMessage message={approval.message}/></p></div></div><div className="mt-4 flex flex-col gap-3 border-t border-[var(--border-subtle)] pt-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11px] text-[var(--text-tertiary)]"><time dateTime={approval.created_at} title={formatDateTime(approval.created_at)} className="inline-flex items-center gap-1.5"><span className="font-medium text-[var(--text-secondary)]">Requested</span>{formatRequested(approval.created_at)}</time><span className="truncate font-mono" title={approval.execution_id}>Execution · {String(approval.execution_id || "").slice(0, 8) || "Unavailable"}</span></div><div className="flex flex-wrap gap-2 sm:shrink-0"><button type="button" onClick={(event) => { event.stopPropagation(); startDecision(approval, "reject"); }} className={rejectButton}>Reject</button><button type="button" onClick={(event) => { event.stopPropagation(); startDecision(approval, "approve"); }} className={primaryButton}>Approve</button></div></div></article>)}</section><Pagination page={page} pageSize={PAGE_SIZE} total={approvals.length} onPageChange={setPage}/></div>}
  </div>;

  return <ProtectedRoute><DashboardShell pageTitle="Approvals">{content}
    {selectedApproval && <div className="fixed inset-0 z-[100] bg-black/50" onMouseDown={(event) => event.target === event.currentTarget && setSelectedApproval(null)}><aside role="dialog" aria-modal="true" aria-labelledby="approval-details-title" className="absolute inset-y-0 right-0 flex w-full max-w-[520px] flex-col border-l border-[var(--border-default)] bg-[var(--surface)] shadow-2xl"><div className="flex items-start justify-between border-b border-[var(--border-subtle)] p-5"><div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--text-tertiary)]">Approval request</p><h2 id="approval-details-title" className="mt-2 text-[19px] font-semibold tracking-tight text-[var(--text-primary)]">Details</h2><div className="mt-2"><StatusBadge status={selectedApproval.status}/></div></div><button ref={closeDetailRef} type="button" onClick={() => setSelectedApproval(null)} aria-label="Close approval details" className="rounded-[6px] border border-[var(--border-subtle)] px-2 py-1 text-[18px] text-[var(--text-tertiary)] hover:bg-[var(--elevated)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/40">×</button></div><div className="flex-1 space-y-6 overflow-y-auto p-5">{detailLoading ? <div role="status" className="space-y-4"><span className="sr-only">Loading approval details</span><div className="h-20 animate-pulse rounded-md bg-[var(--elevated)]"/><div className="h-4 w-1/2 animate-pulse rounded bg-[var(--elevated)]"/><div className="h-4 w-3/4 animate-pulse rounded bg-[var(--elevated)]"/></div> : detailError ? <div className="rounded-md border border-red-500/30 bg-red-500/5 p-4"><p role="alert" className="text-[12px] text-red-600 dark:text-red-400">{detailError}</p>{!detailError.includes("no longer") && <button type="button" onClick={retryDetails} className="mt-3 text-[12px] font-medium text-[var(--accent)] hover:underline">Retry</button>}</div> : <><section><h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Approval message</h3><p className="whitespace-pre-wrap rounded-md border border-[var(--border-subtle)] bg-[var(--elevated)] p-4 text-[13px] leading-6 text-[var(--text-primary)]"><ApprovalMessage message={selectedApproval.message || "No message provided."}/></p></section><section><h3 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-tertiary)]">Request details</h3><dl className="divide-y divide-[var(--border-subtle)] rounded-md border border-[var(--border-subtle)] px-3">{[["Requested", formatDateTime(selectedApproval.created_at)], ["Execution ID", selectedApproval.execution_id], ["Approval ID", selectedApproval.id], ...(selectedApproval.timeout_at ? [["Deadline", formatDateTime(selectedApproval.timeout_at)]] : [])].map(([label, value]) => <div key={label} className="flex flex-col gap-1 py-3 sm:flex-row sm:justify-between sm:gap-4"><dt className="text-[11px] text-[var(--text-tertiary)]">{label}</dt><dd className={`break-all text-[12px] text-[var(--text-secondary)] ${label.endsWith("ID") ? "font-mono" : "sm:text-right"}`}>{value || "Unavailable"}</dd></div>)}</dl></section></>}</div>{!detailLoading && !detailError && String(selectedApproval.status).toLowerCase() === "pending" && <div className="grid grid-cols-2 gap-2 border-t border-[var(--border-subtle)] p-4"><button type="button" onClick={() => startDecision(selectedApproval, "reject")} className={rejectButton}>Reject</button><button type="button" onClick={() => startDecision(selectedApproval, "approve")} className={primaryButton}>Approve</button></div>}</aside></div>}
    <ConfirmDecisionDialog decision={decision} busy={decisionBusy} onCancel={closeDecision} onConfirm={confirmDecision}/>
  </DashboardShell></ProtectedRoute>;
}
