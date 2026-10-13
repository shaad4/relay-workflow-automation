"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { deleteDocument, listDocuments, retryDocument } from "@/services/knowledgeBases";
import Pagination from "@/components/Pagination";
import DocumentUpload, { formatFileSize } from "./DocumentUpload";
import DocumentStatusBadge, { processingStatuses } from "./DocumentStatusBadge";
import DocumentDeleteDialog from "./DocumentDeleteDialog";

const actionButton = "inline-flex h-8 items-center justify-center rounded-md border border-[var(--border-default)] px-2.5 text-[11px] font-medium transition-colors hover:bg-[var(--elevated)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-40";
const deletionBlocked = new Set(["uploading", "parsing", "chunking", "embedding"]);

function formatDate(value) {
  const date = new Date(value);
  return !value || Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function DocumentList({ knowledgeBaseId }) {
  const [documents, setDocuments] = useState(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");
  const [rowBusy, setRowBusy] = useState({});
  const [rowErrors, setRowErrors] = useState({});
  const [deleting, setDeleting] = useState(null);
  const [page, setPage] = useState(1);
  const input = useRef(null);
  const heading = useRef(null);
  const alive = useRef(false);
  const request = useRef(null);
  const sequence = useRef(0);
  const queue = useRef(Promise.resolve());
  const operations = useRef(new Set());

  // Serialize list requests. Only the latest requested snapshot can update the UI.
  const refresh = useCallback(() => {
    const version = ++sequence.current;
    const next = queue.current.then(async () => {
      if (!alive.current || version !== sequence.current) return;
      const controller = new AbortController();
      request.current = controller;
      setRefreshing(true);
      try {
        const data = await listDocuments(knowledgeBaseId, { signal: controller.signal });
        if (!Array.isArray(data)) throw new Error("The document list could not be read. Please try again.");
        if (alive.current && version === sequence.current) {
          setDocuments(data);
          setPage((current) => Math.min(current, Math.max(1, Math.ceil(data.length / 3))));
          setError("");
        }
      } catch (failure) {
        if (alive.current && version === sequence.current && failure.name !== "AbortError") setError(failure.message || "Unable to load documents. Please try again.");
      } finally {
        if (request.current === controller) request.current = null;
        if (alive.current && version === sequence.current) setRefreshing(false);
      }
    });
    queue.current = next;
    return next;
  }, [knowledgeBaseId]);

  useEffect(() => {
    alive.current = true;
    refresh();
    return () => {
      alive.current = false;
      // Invalidate the latest request, not the sequence captured at mount.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      sequence.current++;
      request.current?.abort();
    };
  }, [refresh]);

  const processing = documents?.filter((document) => processingStatuses.has(document.status)).length || 0;
  useEffect(() => {
    if (!processing) return;
    const poll = () => { if (!window.document.hidden && !request.current && operations.current.size === 0) refresh(); };
    const timer = window.setInterval(poll, 2500);
    window.document.addEventListener("visibilitychange", poll);
    return () => { window.clearInterval(timer); window.document.removeEventListener("visibilitychange", poll); };
  }, [processing, refresh]);

  async function operate(document, action) {
    if (operations.current.has(document.id)) return;
    operations.current.add(document.id);
    setRowBusy((current) => ({ ...current, [document.id]: action }));
    setRowErrors((current) => ({ ...current, [document.id]: "" }));
    setMessage("");
    // Invalidate a snapshot started before this mutation.
    sequence.current++;
    request.current?.abort();
    try {
      if (action === "delete") await deleteDocument(knowledgeBaseId, document.id);
      else await retryDocument(knowledgeBaseId, document.id);
      if (!alive.current) return;
      if (action === "delete") {
        setDocuments((current) => current?.filter((item) => item.id !== document.id) ?? null);
        setDeleting(null);
        setMessage(`“${document.filename}” deleted.`);
      } else {
        setMessage(`Retry accepted for “${document.filename}”. Refreshing its status.`);
      }
    } catch (failure) {
      if (alive.current) setRowErrors((current) => ({ ...current, [document.id]: failure.message || `Unable to ${action} this document.` }));
    } finally {
      if (alive.current) {
        await refresh();
        if (alive.current) setRowBusy((current) => ({ ...current, [document.id]: null }));
      }
      operations.current.delete(document.id);
    }
  }

  const ready = documents?.filter((document) => document.status === "ready").length || 0;
  const failed = documents?.filter((document) => document.status === "failed").length || 0;
  const currentPage = Math.min(page, Math.max(1, Math.ceil((documents?.length || 0) / 3)));
  const visibleDocuments = documents?.slice((currentPage - 1) * 3, currentPage * 3);
  return <section aria-labelledby="documents-heading" className="relay-documents overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] shadow-sm">
    <div className="relay-documents-heading px-5 py-6 sm:px-7">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div><p className="mb-2 font-mono text-[9px] uppercase tracking-[.2em] text-[var(--accent)]">Your knowledge, connected</p><div className="flex items-center gap-2.5"><h2 ref={heading} id="documents-heading" tabIndex={-1} className="text-[21px] font-semibold tracking-tight">Documents</h2>{documents && <span className="rounded-md border border-[var(--border-subtle)] bg-[var(--canvas)] px-2 py-0.5 font-mono text-[11px] text-[var(--text-secondary)]">{documents.length}</span>}</div><p className="mt-2 text-[12px] text-[var(--text-secondary)]">Turn your source material into answers your workflows can trust.</p></div>
        {documents && <div className="flex overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--canvas)] shadow-sm">
          {[{ value: ready, label: "Ready", color: "bg-emerald-500" }, { value: processing, label: "Processing", color: "bg-[var(--accent)]" }, { value: failed, label: "Needs attention", color: "bg-amber-500" }].map((metric) => <div key={metric.label} className="min-w-20 border-r border-[var(--border-subtle)] px-3 py-3 last:border-0 sm:min-w-24 sm:px-4"><p className="font-mono text-[20px] leading-6 tracking-tight">{metric.value.toString().padStart(2, "0")}</p><p className="mt-1.5 flex items-center gap-1.5 text-[9px] text-[var(--text-tertiary)]"><span className={`h-1 w-1 rounded-full ${metric.color}`}/>{metric.label}</p></div>)}
        </div>}
      </div>
    </div>
    <DocumentUpload knowledgeBaseId={knowledgeBaseId} onUploaded={refresh} inputRef={input}/>
    <div role="status" aria-live="polite" className="sr-only">{documents ? `${documents.length} documents. ${ready} ready. ${processing} processing. ${failed} failed.` : "Loading documents."}</div>
    {message && <p role="status" className="border-b border-[var(--border-subtle)] bg-[var(--accent)]/5 px-6 py-3 text-[12px] text-[var(--text-secondary)]">{message}</p>}
    {error && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 border-b border-red-500/15 bg-red-500/5 px-6 py-4"><div><p className="text-[12px] font-medium text-red-700 dark:text-red-400">{documents ? "Couldn’t refresh documents" : "Couldn’t load documents"}</p><p className="mt-1 text-[11px] text-[var(--text-secondary)]">{error}{documents ? " Your last loaded documents are shown below." : ""}</p></div><button type="button" onClick={refresh} disabled={refreshing} className={actionButton}>{refreshing ? "Refreshing…" : "Retry"}</button></div>}
    {documents === null && !error && <div aria-label="Loading documents" className="space-y-5 p-6 motion-safe:animate-pulse">{[0, 1, 2].map((index) => <div key={index} className="flex items-center gap-4"><div className="h-10 w-9 rounded-md bg-[var(--elevated)]"/><div className="flex-1 space-y-2"><div className="h-2.5 w-2/5 rounded bg-[var(--elevated)]"/><div className="h-2 w-1/4 rounded bg-[var(--elevated)]"/></div><div className="h-5 w-16 rounded-full bg-[var(--elevated)]"/></div>)}</div>}
    {documents?.length === 0 && <div className="px-6 py-14 text-center"><div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl border border-[var(--border-subtle)] bg-[var(--canvas)] text-[var(--text-tertiary)]"><svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6m-6 4h4"/></svg></div><h3 className="text-[13px] font-medium">No documents uploaded yet</h3><p className="mx-auto mt-2 max-w-sm text-[12px] leading-5 text-[var(--text-tertiary)]">Add a guide, policy, or reference document to give your workflows knowledge they can use.</p><button type="button" onClick={() => input.current?.click()} className="mt-4 rounded text-[12px] font-medium text-[var(--accent-hover)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]">Browse files <span aria-hidden="true">→</span></button></div>}
    {documents?.length > 0 && <>
      <div className="hidden grid-cols-[minmax(0,1fr)_160px_110px_145px] gap-4 border-b border-[var(--border-subtle)] bg-[var(--elevated)]/40 px-6 py-2.5 text-[10px] font-medium text-[var(--text-tertiary)] lg:grid"><span>Name</span><span>Status</span><span>Uploaded</span><span className="text-right">Actions</span></div>
      <ul className="divide-y divide-[var(--border-subtle)]">{visibleDocuments.map((document) => <li key={document.id} className={`relay-document-row px-5 py-5 sm:px-7 ${processingStatuses.has(document.status) ? "relay-document-processing" : ""}`}>
        <div className="grid items-center gap-3 lg:grid-cols-[minmax(0,1fr)_160px_110px_145px] lg:gap-4">
          <div className="flex min-w-0 items-center gap-3"><div className="relay-file-icon grid h-12 w-10 shrink-0 place-items-center rounded-lg border border-[var(--accent)]/20 bg-[var(--accent)]/5 font-mono text-[9px] font-medium uppercase text-[var(--accent)]">{document.filename.split(".").pop()}</div><div className="min-w-0"><p className="break-all text-[13px] font-medium leading-5">{document.filename}</p><p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">{formatFileSize(document.file_size)}<span className="lg:hidden"> · {formatDate(document.created_at)}</span></p></div></div>
          <div><DocumentStatusBadge status={document.status}/></div><time dateTime={document.created_at} className="hidden text-[11px] text-[var(--text-tertiary)] lg:block">{formatDate(document.created_at)}</time>
          <div className="flex items-center gap-2 lg:justify-end">{document.status === "failed" && <button type="button" disabled={!!rowBusy[document.id]} onClick={() => operate(document, "retry")} aria-label={`Retry ingestion for ${document.filename}`} className={actionButton}>{rowBusy[document.id] === "retry" ? "Retrying…" : "Retry"}</button>}<button type="button" disabled={!!rowBusy[document.id] || deletionBlocked.has(document.status)} title={deletionBlocked.has(document.status) ? "Available after processing finishes" : "Delete document"} aria-label={`Delete ${document.filename}${deletionBlocked.has(document.status) ? ": unavailable while processing" : ""}`} onClick={() => { setRowErrors((current) => ({ ...current, [document.id]: "" })); setDeleting(document); }} className={`${actionButton} text-[var(--text-secondary)] hover:text-red-600`}>{rowBusy[document.id] === "delete" ? "Deleting…" : "Delete"}</button></div>
        </div>
        {document.status === "failed" && <p className="mt-2 break-words text-[11px] leading-5 text-red-700 dark:text-red-400">{document.error_message || "Ingestion failed. No additional details are available."} You can retry ingestion.</p>}
        {rowErrors[document.id] && <p role="alert" className="mt-2 text-[11px] text-red-700 dark:text-red-400">{rowErrors[document.id]}</p>}
      </li>)}</ul>
      <div className="border-t border-[var(--border-subtle)] bg-[var(--canvas)] px-5 py-4 sm:px-7">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[10px] text-[var(--text-tertiary)]"><span>{documents.length} {documents.length === 1 ? "document" : "documents"} · 3 per page</span><span className="inline-flex items-center gap-2">{processing > 0 && <span className="relay-live-dot h-1.5 w-1.5 rounded-full bg-[var(--accent)]"/>}{processing ? "Live ingestion updates" : "Library up to date"}</span></div>
        <Pagination page={currentPage} pageSize={3} total={documents.length} onPageChange={setPage}/>
      </div>
    </>}
    {deleting && <DocumentDeleteDialog fallbackFocusRef={heading} document={deleting} busy={!!rowBusy[deleting.id]} error={rowErrors[deleting.id]} onClose={() => setDeleting(null)} onDelete={() => operate(deleting, "delete")}/>}
  </section>;
}
