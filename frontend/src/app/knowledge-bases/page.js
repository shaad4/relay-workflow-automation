"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
} from "@/services/knowledgeBases";

const button =
  "inline-flex h-9 items-center justify-center gap-2 rounded-[7px] px-3.5 text-[12px] font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 disabled:cursor-not-allowed disabled:opacity-50";
const secondaryButton = `${button} border border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]`;
const primaryButton = `${button} bg-[#4F46E5] text-white shadow-sm hover:bg-[#6366F1] active:scale-[.98]`;
const fieldClass =
  "w-full rounded-[8px] border border-[var(--border-default)] bg-[var(--input-bg)] px-3.5 py-2.5 text-[13px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-disabled)] transition-colors focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/15 disabled:opacity-50";

function Icon({ name, className = "h-4 w-4" }) {
  const paths = {
    plus: (
      <>
        <path d="M12 5v14M5 12h14" />
      </>
    ),
    book: (
      <>
        <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 0 4 22z" />
        <path d="M4 5.5v14A2.5 2.5 0 0 1 6.5 17H20M8 7h8M8 10h6" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h14M13 6l6 6-6 6" />
      </>
    ),
    trash: (
      <>
        <path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-4-4" />
      </>
    ),
    alert: (
      <>
        <path d="m10.3 3.9-8.5 14.2a2 2 0 0 0 1.7 3h16.9a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
        <path d="M12 9v4m0 4h.01" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    spark: (
      <>
        <path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />
        <path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9L19 14Z" />
      </>
    ),
  };
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
}

function KnowledgeMark({ name = "Knowledge" }) {
  const hue =
    Array.from(name).reduce((total, char) => total + char.charCodeAt(0), 0) %
    360;
  return (
    <div className="relative grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--elevated)] text-[var(--text-primary)]">
      <span
        className="absolute inset-0 opacity-20"
        style={{
          background: `radial-gradient(circle at 30% 20%, hsl(${hue} 85% 65%), transparent 72%)`,
        }}
      />
      <Icon name="book" className="relative h-[21px] w-[21px]" />
      <span className="absolute bottom-1 right-1 h-1.5 w-1.5 rounded-full bg-[var(--accent)] ring-2 ring-[var(--surface)]" />
    </div>
  );
}

function Dialog({ title, description, onClose, children, danger = false }) {
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/65 p-4 backdrop-blur-sm animate-in fade-in duration-150"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="kb-dialog-title"
        className="my-auto w-full max-w-lg overflow-hidden rounded-2xl border border-[var(--border-default)] bg-[var(--surface)] shadow-2xl animate-in zoom-in-95 duration-150"
      >
        <div className="border-b border-[var(--border-subtle)] px-5 py-4 sm:px-6">
          <div className="flex items-start gap-3">
            <div
              className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg border ${danger ? "border-red-500/20 bg-red-500/10 text-red-400" : "border-[var(--accent)]/20 bg-[var(--accent)]/10 text-[var(--accent)]"}`}
            >
              <Icon name={danger ? "trash" : "book"} className="h-4 w-4" />
            </div>
            <div className="min-w-0 pt-0.5">
              <h2
                id="kb-dialog-title"
                className="text-[15px] font-semibold tracking-tight"
              >
                {title}
              </h2>
              {description && (
                <p className="mt-1 text-[12px] leading-5 text-[var(--text-secondary)]">
                  {description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close dialog"
              className="ml-auto rounded-md px-2 py-1 text-[var(--text-tertiary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]"
            >
              ×
            </button>
          </div>
        </div>
        <div className="p-5 sm:p-6">{children}</div>
      </section>
    </div>
  );
}

function KnowledgeBasesContent() {
  const { isInitializing } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);
  const [query, setQuery] = useState("");
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState("");
  const [retry, setRetry] = useState(0);

  const flash = useCallback((message) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 2800);
  }, []);
  const closeModal = useCallback(() => {
    if (!saving && !deleting) {
      setModal(null);
      setFormError("");
    }
  }, [saving, deleting]);
  useEffect(() => {
    document.title = "Knowledge Bases | Relay";
  }, []);
  useEffect(() => {
    if (isInitializing) return;
    let active = true;
    setLoading(true);
    listKnowledgeBases()
      .then((data) => {
        if (active) {
          setItems(Array.isArray(data) ? data : []);
          setError(false);
        }
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isInitializing, reload, retry]);

  const filtered = items.filter((item) =>
    `${item.name || ""} ${item.description || ""}`
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  );
  const openCreate = () => {
    setName("");
    setDescription("");
    setFormError("");
    setModal("create");
  };
  const submit = async (event) => {
    event.preventDefault();
    const cleanName = name.trim();
    if (!cleanName || cleanName.length > 255) {
      setFormError("Enter a name between 1 and 255 characters.");
      return;
    }
    if (description.length > 1000) {
      setFormError("Description must be 1000 characters or fewer.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await createKnowledgeBase({
        name: cleanName,
        description: description.trim() || null,
      });
      setModal(null);
      setName("");
      setDescription("");
      flash("Knowledge base created.");
      setReload((value) => value + 1);
    } catch (requestError) {
      setFormError(
        requestError?.message ||
          "Unable to create knowledge base. Check the details and try again.",
      );
    } finally {
      setSaving(false);
    }
  };
  const remove = async () => {
    if (!selected) return;
    setDeleting(true);
    setFormError("");
    try {
      await deleteKnowledgeBase(selected.id);
      setItems((current) => current.filter((item) => item.id !== selected.id));
      setModal(null);
      setSelected(null);
      flash("Knowledge base deleted.");
    } catch (requestError) {
      setFormError(
        requestError?.message ||
          "Unable to delete this knowledge base. Try again.",
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="Knowledge Bases">
        <div className="w-full min-w-0 space-y-6 font-sans">
          <header className="flex flex-col gap-5 border-b border-[var(--border-subtle)] pb-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-[.18em] text-[var(--text-tertiary)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
                Workspace resources
              </div>
              <h1 className="text-[26px] font-semibold leading-8 tracking-tight text-[var(--text-primary)] sm:text-[30px]">
                Knowledge Bases
              </h1>
              <p className="mt-1.5 max-w-xl text-[13px] leading-5 text-[var(--text-secondary)]">
                A reliable source of truth for every workflow that needs to know
                your business.
              </p>
            </div>
            <button
              type="button"
              onClick={openCreate}
              className={`${primaryButton} h-10 px-4`}
            >
              <Icon name="plus" className="h-4 w-4" />
              Create Knowledge Base
            </button>
          </header>
          {notice && (
            <div
              role="status"
              className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/[.08] px-3.5 py-2.5 text-[12px] text-emerald-400"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              {notice}
            </div>
          )}
          {!loading && !error && items.length > 0 && (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2 text-[12px] text-[var(--text-tertiary)]">
                <span className="font-mono text-[var(--text-primary)]">
                  {items.length.toString().padStart(2, "0")}
                </span>
                {items.length === 1 ? "knowledge base" : "knowledge bases"}
                <span className="mx-1 h-3 w-px bg-[var(--border-default)]" />
                <span>Ready to power RAG workflows</span>
              </div>
              <label className="relative block w-full sm:w-64">
                <Icon
                  name="search"
                  className="absolute left-3 top-2.5 h-4 w-4 text-[var(--text-tertiary)]"
                />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  aria-label="Search knowledge bases"
                  placeholder="Search your library..."
                  className={`${fieldClass} h-9 pl-9 text-[12px]`}
                />
              </label>
            </div>
          )}
          {loading && (
            <div
              aria-label="Loading knowledge bases"
              role="status"
              className="grid grid-cols-1 gap-3.5 animate-pulse md:grid-cols-2 xl:grid-cols-3"
            >
              {[1, 2, 3].map((key) => (
                <div
                  key={key}
                  className="flex min-h-[210px] flex-col rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4"
                >
                  <div className="flex gap-3">
                    <div className="h-12 w-12 rounded-xl bg-[var(--elevated)]" />
                    <div className="flex-1 space-y-2 pt-1">
                      <div className="h-4 w-3/5 rounded bg-[var(--elevated)]" />
                      <div className="h-3 w-2/5 rounded bg-[var(--elevated)]" />
                    </div>
                  </div>
                  <div className="mt-5 space-y-2">
                    <div className="h-3 w-full rounded bg-[var(--elevated)]" />
                    <div className="h-3 w-4/5 rounded bg-[var(--elevated)]" />
                  </div>
                  <div className="mt-auto border-t border-[var(--border-subtle)] pt-3">
                    <div className="h-3 w-2/3 rounded bg-[var(--elevated)]" />
                  </div>
                </div>
              ))}
            </div>
          )}
          {!loading && error && (
            <section className="my-4 rounded-2xl border border-red-500/20 bg-[var(--surface)] px-8 py-12 text-center">
              <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl border border-red-500/20 bg-red-500/10 text-red-400">
                <Icon name="alert" className="h-5 w-5" />
              </div>
              <h2 className="text-[16px] font-semibold tracking-tight">
                Your library couldn’t load
              </h2>
              <p className="mx-auto mt-1 max-w-sm text-[13px] leading-5 text-[var(--text-secondary)]">
                Check your connection and try again. Your knowledge bases are
                safe.
              </p>
              <button
                type="button"
                onClick={() => setRetry((value) => value + 1)}
                className={`${secondaryButton} mt-5`}
              >
                Retry loading
              </button>
            </section>
          )}
          {!loading && !error && items.length === 0 && (
            <section className="relative my-2 overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] px-6 py-12 text-center sm:px-12 sm:py-16">
              <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-[radial-gradient(ellipse_at_50%_0,rgba(99,102,241,.11),transparent_70%)]" />
              <div className="relative mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl border border-[var(--accent)]/20 bg-[var(--accent)]/10 text-[var(--accent)] shadow-[0_0_36px_rgba(99,102,241,.10)]">
                <Icon name="book" className="h-6 w-6" />
              </div>
              <p className="relative mb-2 text-[10px] font-mono uppercase tracking-[.17em] text-[var(--accent)]">
                Build your knowledge layer
              </p>
              <h2 className="relative text-[18px] font-semibold tracking-tight sm:text-[20px]">
                No knowledge bases yet
              </h2>
              <p className="relative mx-auto mt-2 max-w-md text-[13px] leading-6 text-[var(--text-secondary)]">
                Create a knowledge base to organize the documents your AI
                workflows can use as a trusted source.
              </p>
              <button
                type="button"
                onClick={openCreate}
                className={`${primaryButton} relative mt-6 h-10 px-4`}
              >
                <Icon name="plus" className="h-4 w-4" />
                Create your first knowledge base
              </button>
              <div className="relative mx-auto mt-10 grid max-w-xl grid-cols-3 divide-x divide-[var(--border-subtle)] border-t border-[var(--border-subtle)] pt-5 text-left">
                <div className="px-3">
                  <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                    01
                  </span>
                  <p className="mt-1 text-[11px] font-medium">Organize</p>
                </div>
                <div className="px-3">
                  <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                    02
                  </span>
                  <p className="mt-1 text-[11px] font-medium">
                    Connect to workflows
                  </p>
                </div>
                <div className="px-3">
                  <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                    03
                  </span>
                  <p className="mt-1 text-[11px] font-medium">
                    Answer with context
                  </p>
                </div>
              </div>
            </section>
          )}
          {!loading && !error && items.length > 0 && filtered.length === 0 && (
            <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] px-6 py-12 text-center">
              <Icon
                name="search"
                className="mx-auto h-5 w-5 text-[var(--text-tertiary)]"
              />
              <h2 className="mt-3 text-[14px] font-semibold">
                No matching knowledge bases
              </h2>
              <p className="mt-1 text-[12px] text-[var(--text-secondary)]">
                Try a different name or description.
              </p>
            </div>
          )}
          {!loading && !error && filtered.length > 0 && (
            <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2 xl:grid-cols-3">
              {filtered.map((item) => (
                <article
                  key={item.id}
                  className="group relative flex min-h-[224px] flex-col overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 shadow-sm transition-all duration-150 hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:shadow-lg"
                >
                  <Link
                    href={`/dashboard/knowledge-bases/${encodeURIComponent(item.id)}`}
                    aria-label={`Open ${item.name}`}
                    className="absolute inset-0 z-0 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50"
                  />
                  <div className="relative z-10 flex items-start gap-3 pr-8 pointer-events-none">
                    <KnowledgeMark name={item.name} />
                    <div className="min-w-0 flex-1 pt-0.5">
                      <h2 className="truncate text-[15px] font-semibold tracking-tight text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
                        {item.name}
                      </h2>
                      <p className="mt-1 truncate font-mono text-[10px] text-[var(--text-tertiary)]">
                        /knowledge-bases/{String(item.id || "").slice(0, 8)}
                      </p>
                    </div>
                  </div>
                  <p className="relative z-10 mt-4 min-h-[58px] pointer-events-none text-[13px] leading-[19px] text-[var(--text-secondary)] line-clamp-3">
                    {item.description || (
                      <span className="italic text-[var(--text-tertiary)]">
                        A shared source of knowledge for your workflows.
                      </span>
                    )}
                  </p>
                  <div className="relative z-20 mt-auto flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3">
                    <div className="flex min-w-0 items-center gap-2 text-[11px] text-[var(--text-tertiary)]">
                      <Icon name="clock" className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">
                        Created {formatDate(item.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => {
                          setSelected(item);
                          setFormError("");
                          setModal("delete");
                        }}
                        aria-label={`Delete ${item.name}`}
                        className="grid h-7 w-7 place-items-center rounded-md text-[var(--text-tertiary)] transition-colors hover:bg-red-500/10 hover:text-red-400 focus:outline-none focus:ring-2 focus:ring-red-500/30"
                      >
                        <Icon name="trash" className="h-3.5 w-3.5" />
                      </button>
                      <Link
                        href={`/dashboard/knowledge-bases/${encodeURIComponent(item.id)}`}
                        className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] font-semibold text-[var(--accent)] transition-colors hover:bg-[var(--accent)]/10"
                      >
                        Open
                        <Icon
                          name="arrow"
                          className="h-3 w-3 transition-transform group-hover:translate-x-0.5"
                        />
                      </Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
          {modal === "create" && (
            <Dialog
              title="Create a knowledge base"
              description="Give this library a clear name so your team can find it when building workflows."
              onClose={closeModal}
            >
              <form onSubmit={submit} className="grid gap-4" noValidate>
                <div className="grid gap-1.5">
                  <label
                    htmlFor="kb-name"
                    className="text-[12px] font-medium text-[var(--text-secondary)]"
                  >
                    Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    id="kb-name"
                    autoFocus
                    maxLength={255}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="e.g. Refund & Return Policies"
                    className={fieldClass}
                    aria-describedby="kb-name-hint kb-form-error"
                  />
                  <div
                    id="kb-name-hint"
                    className="flex justify-between text-[10px] text-[var(--text-tertiary)]"
                  >
                    <span>Choose a name your team will recognize.</span>
                    <span>{name.length}/255</span>
                  </div>
                </div>
                <div className="grid gap-1.5">
                  <label
                    htmlFor="kb-description"
                    className="text-[12px] font-medium text-[var(--text-secondary)]"
                  >
                    Description{" "}
                    <span className="font-normal text-[var(--text-tertiary)]">
                      · optional
                    </span>
                  </label>
                  <textarea
                    id="kb-description"
                    maxLength={1000}
                    rows={4}
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Describe what this knowledge base contains..."
                    className={`${fieldClass} min-h-24 resize-y`}
                    aria-describedby="kb-desc-hint"
                  />
                  <span
                    id="kb-desc-hint"
                    className="text-right text-[10px] text-[var(--text-tertiary)]"
                  >
                    {description.length}/1000
                  </span>
                </div>
                {formError && (
                  <p
                    id="kb-form-error"
                    role="alert"
                    className="rounded-lg border border-red-500/20 bg-red-500/[.08] px-3 py-2 text-[12px] text-red-400"
                  >
                    {formError}
                  </p>
                )}
                <div className="mt-1 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
                  <button
                    type="button"
                    disabled={saving}
                    onClick={closeModal}
                    className={secondaryButton}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className={primaryButton}
                  >
                    {saving ? (
                      <>
                        <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                        Creating…
                      </>
                    ) : (
                      <>
                        <Icon name="plus" className="h-3.5 w-3.5" />
                        Create knowledge base
                      </>
                    )}
                  </button>
                </div>
              </form>
            </Dialog>
          )}
          {modal === "delete" && (
            <Dialog
              title="Delete this knowledge base?"
              description="This will permanently remove its associated database document and chunk records."
              onClose={closeModal}
              danger
            >
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--elevated)]/50 p-3.5">
                <div className="flex items-center gap-3">
                  <KnowledgeMark name={selected?.name} />
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-semibold">
                      {selected?.name}
                    </p>
                    <p className="mt-0.5 text-[11px] text-[var(--text-tertiary)]">
                      External files may remain stored.
                    </p>
                  </div>
                </div>
              </div>
              <p className="mt-3 text-[12px] leading-5 text-[var(--text-secondary)]">
                This action cannot be undone. Physical external files are not
                confirmed to be deleted.
              </p>
              {formError && (
                <p role="alert" className="mt-3 text-[12px] text-red-400">
                  {formError}
                </p>
              )}
              <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-4">
                <button
                  type="button"
                  disabled={deleting}
                  onClick={closeModal}
                  className={secondaryButton}
                >
                  Keep knowledge base
                </button>
                <button
                  type="button"
                  disabled={deleting}
                  onClick={remove}
                  className={`${button} bg-red-600 text-white hover:bg-red-500`}
                >
                  {deleting ? (
                    "Deleting…"
                  ) : (
                    <>
                      <Icon name="trash" className="h-3.5 w-3.5" />
                      Delete
                    </>
                  )}
                </button>
              </div>
            </Dialog>
          )}
        </div>
      </DashboardShell>
    </ProtectedRoute>
  );
}

export default function KnowledgeBasesPage() {
  return <KnowledgeBasesContent />;
}
