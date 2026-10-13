"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DocumentList from "@/components/knowledge-bases/DocumentList";
import DashboardShell from "@/components/dashboard/DashboardShell";
import { deleteKnowledgeBase, getKnowledgeBase } from "@/services/knowledgeBases";

const button = "inline-flex h-9 items-center justify-center gap-2 rounded-[7px] px-3.5 text-[12px] font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 disabled:cursor-not-allowed disabled:opacity-50";
const secondaryButton = `${button} border border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]`;

function Icon({ name, className = "h-4 w-4" }) {
  const paths = {
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 0 4 22z"/><path d="M4 5.5v14A2.5 2.5 0 0 1 6.5 17H20M8 7h8M8 10h6"/></>,
    back: <><path d="M19 12H5m7 7-7-7 7-7"/></>,
    upload: <><path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    alert: <><path d="m10.3 3.9-8.5 14.2a2 2 0 0 0 1.7 3h16.9a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/></>,
    trash: <><path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/></>,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">{paths[name]}</svg>;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

function DeleteDialog({ name, onClose, onDelete, busy, error }) {
  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === "Escape" && !busy) onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, busy]);
  return <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/65 p-4 backdrop-blur-sm animate-in fade-in duration-150"><section role="dialog" aria-modal="true" aria-labelledby="kb-delete-title" className="my-auto w-full max-w-lg overflow-hidden rounded-2xl border border-[var(--border-default)] bg-[var(--surface)] shadow-2xl animate-in zoom-in-95 duration-150"><div className="flex items-start gap-3 border-b border-[var(--border-subtle)] px-5 py-4 sm:px-6"><div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-red-500/20 bg-red-500/10 text-red-400"><Icon name="trash" className="h-4 w-4"/></div><div><h2 id="kb-delete-title" className="text-[15px] font-semibold">Delete this knowledge base?</h2><p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">Associated database document and chunk records will be removed.</p></div></div><div className="p-5 sm:p-6"><p className="text-[13px] text-[var(--text-secondary)]">Delete <strong className="text-[var(--text-primary)]">{name}</strong>? This cannot be undone. Physical external files may remain.</p>{error && <p role="alert" className="mt-3 text-[12px] text-red-400">{error}</p>}<div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4"><button type="button" disabled={busy} onClick={onClose} className={secondaryButton}>Cancel</button><button type="button" disabled={busy} onClick={onDelete} className={`${button} bg-red-600 text-white hover:bg-red-500`}>{busy ? "Deleting…" : <><Icon name="trash" className="h-3.5 w-3.5"/>Delete knowledge base</>}</button></div></div></section></div>;
}

function KnowledgeBaseDetailsContent() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id;
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const closeDialog = useCallback(() => { if (!deleting) { setConfirming(false); setDeleteError(""); } }, [deleting]);

  useEffect(() => { document.title = `${item?.name || "Knowledge Base"} | Relay`; }, [item?.name]);
  useEffect(() => {
    if (!id) return;
    let active = true;
    getKnowledgeBase(id).then((data) => { if (active) setItem(data); }).catch((requestError) => { if (active) { if (requestError?.status === 404) setNotFound(true); else setError(requestError?.message || "Unable to load this knowledge base."); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, retry]);

  const remove = async () => {
    setDeleting(true); setDeleteError("");
    try { await deleteKnowledgeBase(id); router.push("/dashboard/knowledge-bases"); }
    catch (requestError) {
      if (requestError?.status === 404) setDeleteError("This knowledge base was already deleted.");
      else if (requestError?.status === 403) setDeleteError("You do not have access to delete this knowledge base.");
      else setDeleteError(requestError?.message || "Unable to delete this knowledge base. Check your connection and try again.");
    } finally { setDeleting(false); }
  };

  return <DashboardShell pageTitle="Knowledge Bases"><div className="mx-auto w-full max-w-[1440px] space-y-5 font-sans"><Link href="/dashboard/knowledge-bases" className="inline-flex items-center gap-2 text-[12px] font-medium text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"><Icon name="back" className="h-3.5 w-3.5"/>All knowledge bases</Link>
    {loading && <div className="grid gap-4 animate-pulse"><div className="h-4 w-36 rounded bg-[var(--elevated)]"/><div className="h-48 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)]"/><div className="h-64 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)]"/></div>}
    {!loading && notFound && <section className="my-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] px-8 py-12 text-center"><div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl border border-[var(--border-subtle)] bg-[var(--elevated)] text-[var(--text-tertiary)]"><Icon name="book" className="h-5 w-5"/></div><h1 className="text-[17px] font-semibold tracking-tight">Knowledge base not found</h1><p className="mt-1 text-[13px] text-[var(--text-secondary)]">It may have been deleted or you may not have access to it.</p><Link href="/dashboard/knowledge-bases" className={`${secondaryButton} mt-5`}>Return to your library</Link></section>}
    {!loading && error && <section className="my-4 rounded-2xl border border-red-500/20 bg-[var(--surface)] px-8 py-12 text-center"><div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl border border-red-500/20 bg-red-500/10 text-red-400"><Icon name="alert" className="h-5 w-5"/></div><h1 className="text-[16px] font-semibold">Couldn’t open this knowledge base</h1><p className="mt-1 text-[13px] text-[var(--text-secondary)]">{error}</p><button type="button" onClick={() => { setLoading(true); setError(false); setNotFound(false); setRetry((value) => value + 1); }} className={`${secondaryButton} mt-5`}>Try again</button></section>}
    {!loading && !error && !notFound && item && <><section className="relative overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 shadow-sm sm:p-7"><div className="pointer-events-none absolute right-0 top-0 h-48 w-64 bg-[radial-gradient(ellipse_at_100%_0,rgba(99,102,241,.12),transparent_70%)]"/><div className="relative flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between"><div className="flex min-w-0 items-start gap-4"><div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl border border-[var(--accent)]/20 bg-[var(--accent)]/10 text-[var(--accent)]"><Icon name="book" className="h-6 w-6"/></div><div className="min-w-0"><div className="mb-1.5 flex items-center gap-2 text-[10px] font-mono uppercase tracking-[.17em] text-[var(--text-tertiary)]"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400"/>Knowledge library</div><h1 className="break-words text-[23px] font-semibold leading-7 tracking-tight sm:text-[27px]">{item.name}</h1><p className="mt-2 max-w-3xl whitespace-pre-wrap text-[13px] leading-5 text-[var(--text-secondary)]">{item.description || <span className="italic text-[var(--text-tertiary)]">No description added yet.</span>}</p></div></div><button type="button" onClick={() => { setDeleteError(""); setConfirming(true); }} className="inline-flex h-8 shrink-0 items-center gap-2 self-start rounded-[6px] px-2.5 text-[11px] font-medium text-[var(--text-tertiary)] transition-colors hover:bg-red-500/10 hover:text-red-400"><Icon name="trash" className="h-3.5 w-3.5"/>Delete knowledge base</button></div><div className="relative mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-[var(--border-subtle)] pt-4 text-[11px] text-[var(--text-tertiary)]"><span className="inline-flex items-center gap-1.5"><Icon name="clock" className="h-3.5 w-3.5"/>Created {formatDate(item.created_at)}</span><span className="h-3 w-px bg-[var(--border-default)]"/><span className="font-mono">ID · {String(item.id || id).slice(0, 8)}</span></div></section>
      <DocumentList key={id} knowledgeBaseId={id}/></>}
  </div>{confirming && item && <DeleteDialog name={item.name} onClose={closeDialog} onDelete={remove} busy={deleting} error={deleteError}/>}</DashboardShell>;
}

export default function KnowledgeBaseDetailsPage() {
  const params = useParams();
  return <ProtectedRoute><KnowledgeBaseDetailsContent key={params?.id} /></ProtectedRoute>;
}
