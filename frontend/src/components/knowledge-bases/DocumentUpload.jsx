"use client";

import { useEffect, useRef, useState } from "react";
import { uploadDocument } from "@/services/knowledgeBases";

export function formatFileSize(size) {
  if (!Number.isFinite(size) || size < 0) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MiB`;
}

export default function DocumentUpload({ knowledgeBaseId, onUploaded, inputRef }) {
  const [files, setFiles] = useState([]);
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const running = useRef(false);
  const controller = useRef(null);
  useEffect(() => () => controller.current?.abort(), []);

  function selectFiles(selected) {
    if (running.current) return;
    const existing = files.filter((entry) => entry.status === "selected");
    const incoming = Array.from(selected);
    if (existing.length + incoming.length > 5) {
      setErrors(["Choose up to five files per batch. Remove a selected file or choose fewer files."]);
      return;
    }
    const validation = [];
    const accepted = [];
    for (const file of incoming) {
      if (!/\.(pdf|txt|md)$/i.test(file.name)) validation.push(`${file.name}: choose a PDF, TXT, or Markdown (.md) file.`);
      else if (file.size > 10 * 1024 * 1024) validation.push(`${file.name}: exceeds the 10 MiB limit.`);
      else if (!file.size) validation.push(`${file.name}: empty files cannot be uploaded.`);
      else accepted.push({ id: crypto.randomUUID(), file, status: "selected" });
    }
    setErrors(validation);
    setFiles([...existing, ...accepted]);
  }

  async function upload() {
    if (running.current) return;
    running.current = true;
    setBusy(true);
    setErrors([]);
    const abort = new AbortController();
    controller.current = abort;
    const update = (id, values) => setFiles((current) => current.map((entry) => entry.id === id ? { ...entry, ...values } : entry));
    try {
      for (const entry of files.filter((file) => file.status === "selected")) {
        if (abort.signal.aborted) break;
        update(entry.id, { status: "uploading" });
        try {
          await uploadDocument(knowledgeBaseId, entry.file, { signal: abort.signal });
          if (!abort.signal.aborted) update(entry.id, { status: "uploaded" });
        } catch (error) {
          if (abort.signal.aborted) break;
          update(entry.id, { status: "failed", error: `${error.message || "Upload could not be confirmed."} Check the document list before selecting this file again; it may already have been saved.` });
          if (error.status === 401) break;
        }
        if (!abort.signal.aborted) await onUploaded();
      }
    } finally {
      running.current = false;
      if (!abort.signal.aborted) setBusy(false);
    }
  }

  const selectedCount = files.filter((entry) => entry.status === "selected").length;
  return <div className="border-b border-[var(--border-subtle)] p-5 sm:p-7">
    <input ref={inputRef} type="file" accept=".pdf,.txt,.md" multiple disabled={busy} className="hidden" aria-label="Choose documents" onChange={(event) => { selectFiles(event.target.files); event.target.value = ""; }}/>
    <div onDragOver={(event) => { event.preventDefault(); if (!busy) setDragging(true); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }} onDrop={(event) => { event.preventDefault(); setDragging(false); selectFiles(event.dataTransfer.files); }} className={`relay-upload-zone group relative flex flex-col items-center justify-between gap-5 overflow-hidden rounded-xl border px-6 py-8 transition-colors sm:flex-row ${dragging ? "border-[var(--accent)] bg-[var(--accent)]/5" : "border-[var(--border-subtle)] bg-[var(--canvas)]"}`}>
      <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:text-left">
        <div className="relay-upload-art" aria-hidden="true"><span className="relay-upload-sheet relay-upload-sheet-back">MD</span><span className="relay-upload-sheet relay-upload-sheet-front"><svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5"/></svg><span className="mt-2 h-px w-5 bg-current opacity-20"/><span className="mt-1 h-px w-3 bg-current opacity-20"/></span></div>
        <div className="relative"><p className="text-[16px] font-semibold tracking-tight">A smarter workflow starts with a file.</p><p className="mt-1.5 text-[12px] text-[var(--text-secondary)]">Drop your documents here, or browse to get started.</p><div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-[9px] text-[var(--text-tertiary)] sm:justify-start">{["PDF", "TXT", "MD"].map((type) => <span key={type} className="rounded border border-[var(--border-default)] bg-[var(--surface)] px-1.5 py-0.5 font-mono">{type}</span>)}<span className="ml-1">10 MiB each · 5 files per batch</span></div></div>
      </div>
      <button type="button" disabled={busy} onClick={() => inputRef.current?.click()} className="relative inline-flex h-10 shrink-0 items-center rounded-lg bg-[var(--accent)] px-4 text-[12px] font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-[var(--accent-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:opacity-50 motion-reduce:transform-none">Browse files <span className="ml-3 text-white/70" aria-hidden="true">↑</span></button>
    </div>
    {errors.length > 0 && <ul role="alert" className="mt-3 space-y-1 text-[12px] text-red-700 dark:text-red-400">{errors.map((error) => <li key={error}>{error}</li>)}</ul>}
    {files.length > 0 && <div className="mt-4 overflow-hidden rounded-lg border border-[var(--border-subtle)]">
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--elevated)]/50 px-4 py-2 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]"><span>Upload batch</span><span>{files.length} / 5 files</span></div>
      <ul className="divide-y divide-[var(--border-subtle)]">{files.map((entry) => <li key={entry.id} className="px-4 py-3">
        <div className="flex items-center gap-3"><span className="rounded border border-[var(--border-default)] px-1.5 py-1 font-mono text-[9px] uppercase text-[var(--text-secondary)]">{entry.file.name.split(".").pop()}</span><div className="min-w-0 flex-1"><p className="break-all text-[12px] font-medium">{entry.file.name}</p><p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">{formatFileSize(entry.file.size)}</p></div><span role="status" className="inline-flex items-center gap-2 text-[11px] text-[var(--text-secondary)]">{entry.status === "uploading" && <span className="relay-ingestion-bars" aria-hidden="true"><i/><i/><i/></span>}{{ selected: "Selected", uploading: "Uploading…", uploaded: "Uploaded ✓", failed: "Not confirmed" }[entry.status]}</span>{entry.status === "selected" && <button type="button" disabled={busy} aria-label={`Remove ${entry.file.name}`} onClick={() => setFiles((current) => current.filter((file) => file.id !== entry.id))} className="rounded px-2 py-1 text-[var(--text-tertiary)] hover:bg-[var(--elevated)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] disabled:opacity-50">×</button>}</div>
        {entry.error && <p role="alert" className="mt-2 break-words text-[11px] leading-5 text-red-700 dark:text-red-400">{entry.error}</p>}
      </li>)}</ul>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border-subtle)] px-4 py-3"><p className="text-[11px] text-[var(--text-tertiary)]">Files are processed automatically after upload.</p>{selectedCount > 0 || busy ? <button type="button" disabled={busy} onClick={upload} className="h-8 rounded-[7px] bg-[var(--accent)] px-3 text-[11px] font-medium text-white hover:bg-[var(--accent-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:opacity-50">{busy ? "Uploading…" : `Upload ${selectedCount} ${selectedCount === 1 ? "file" : "files"}`}</button> : <button type="button" onClick={() => { setFiles([]); setErrors([]); inputRef.current?.click(); }} className="rounded text-[11px] font-medium text-[var(--accent-hover)] focus-visible:outline-2 focus-visible:outline-[var(--accent)]">Choose another batch →</button>}</div>
    </div>}
  </div>;
}
