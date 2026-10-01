"use client";

import { useEffect, useRef, useState } from "react";
import WorkflowStatus from "../workflows/WorkflowStatus";
import { activateWorkflow, deactivateWorkflow, deleteWorkflow, deleteWorkflowVersion, updateWorkflow } from "@/services/workflows";

function CheckIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <polyline points="20 6 9 17 4 12" />
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

function ShieldCheckIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <polyline points="9 12 11 14 15 10" />
    </svg>
  );
}

function RocketIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
      <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-3.05 11a22.35 22.35 0 0 1-3.95 2z" />
    </svg>
  );
}

function EditIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function RefreshCwIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

export default function WorkflowToolbar({
  workflowName = "Workflow",
  workflowStatus = "draft",
  workflowDescription = "",
  workflowId,
  onWorkflowUpdated,
  onWorkflowStatusChange,
  onWorkflowDeleted,
  onNavigate,
  versionNumber = 1,
  versions = [],
  publishedVersionId,
  onSelectVersion,
  saveState = "saved", // 'saved' | 'unsaved' | 'saving' | 'failed'
  saveError = null,
  isReadOnly = false,
  onSave,
  onValidate,
  onPublish,
  onEditWorkflow,
  isValidating = false,
  isPublishing = false,
  isCreatingDraft = false,
  canUndo = false,
  canRedo = false,
  onUndo,
  onRedo,
}) {
  const [editingMetadata, setEditingMetadata] = useState(false);
  const [nameDraft, setNameDraft] = useState(workflowName);
  const [descriptionDraft, setDescriptionDraft] = useState(workflowDescription);
  const [metadataError, setMetadataError] = useState("");
  const [isSavingMetadata, setIsSavingMetadata] = useState(false);
  const [isTogglingWorkflow, setIsTogglingWorkflow] = useState(false);
  const [showWorkflowStatusConfirm, setShowWorkflowStatusConfirm] = useState(false);
  const [workflowStatusError, setWorkflowStatusError] = useState("");
  const [workflowMenuOpen, setWorkflowMenuOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeletingWorkflow, setIsDeletingWorkflow] = useState(false);
  const [deleteWorkflowError, setDeleteWorkflowError] = useState("");
  const [versionMenuOpen, setVersionMenuOpen] = useState(false);
  const [versionToDelete, setVersionToDelete] = useState(null);
  const [isDeletingVersion, setIsDeletingVersion] = useState(false);
  const [deleteVersionError, setDeleteVersionError] = useState("");
  const workflowMenuRef = useRef(null);
  const versionMenuRef = useRef(null);
  // Older workflow payloads may expose "published"; the workflow-level state is active.
  const normalizedWorkflowStatus = String(workflowStatus).toLowerCase() === "published"
    ? "active"
    : String(workflowStatus).toLowerCase();
  const canDeleteWorkflow = normalizedWorkflowStatus === "draft" || normalizedWorkflowStatus === "inactive";
  const sortedVersions = [...versions].sort((a, b) =>
    Number(b.version_number ?? b.version) - Number(a.version_number ?? a.version)
  );
  const currentVersion = sortedVersions.find(
    (item) => Number(item.version_number ?? item.version) === Number(versionNumber)
  );
  const hasDraftVersion = sortedVersions.some((item) => String(item.status).toLowerCase() === "draft");

  useEffect(() => {
    if (!workflowMenuOpen) return;
    const closeOnOutsideClick = (event) => {
      if (!workflowMenuRef.current?.contains(event.target)) setWorkflowMenuOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setWorkflowMenuOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [workflowMenuOpen]);

  useEffect(() => {
    if (!versionMenuOpen) return;
    const closeOnOutsideClick = (event) => {
      if (!versionMenuRef.current?.contains(event.target)) setVersionMenuOpen(false);
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setVersionMenuOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [versionMenuOpen]);

  const startMetadataEdit = () => {
    setNameDraft(workflowName);
    setDescriptionDraft(workflowDescription);
    setMetadataError("");
    setEditingMetadata(true);
  };

  const saveMetadata = async (event) => {
    event.preventDefault();
    const name = nameDraft.trim();
    if (!name) {
      setMetadataError("Workflow name is required.");
      return;
    }
    setIsSavingMetadata(true);
    setMetadataError("");
    try {
      await updateWorkflow(workflowId, {
        name,
        description: descriptionDraft.trim() || null,
      });
      setEditingMetadata(false);
      onWorkflowUpdated?.();
    } catch (error) {
      setMetadataError(error?.message || "Unable to update workflow details.");
    } finally {
      setIsSavingMetadata(false);
    }
  };

  const confirmDeleteWorkflow = async () => {
    if (isDeletingWorkflow) return;
    setIsDeletingWorkflow(true);
    setDeleteWorkflowError("");
    try {
      await deleteWorkflow(workflowId);
      setShowDeleteConfirm(false);
      onWorkflowDeleted?.();
    } catch (error) {
      setDeleteWorkflowError(error?.message || "Unable to delete workflow.");
    } finally {
      setIsDeletingWorkflow(false);
    }
  };

  const confirmDeleteVersion = async () => {
    if (!versionToDelete || isDeletingVersion) return;
    setIsDeletingVersion(true);
    setDeleteVersionError("");
    try {
      await deleteWorkflowVersion(workflowId, versionToDelete.version_number ?? versionToDelete.version);
      setVersionToDelete(null);
      setVersionMenuOpen(false);
      await onWorkflowUpdated?.();
    } catch (error) {
      setDeleteVersionError(error?.message || "Unable to delete this workflow version.");
    } finally {
      setIsDeletingVersion(false);
    }
  };

  const toggleWorkflowStatus = async () => {
    if (isTogglingWorkflow) return;
    setIsTogglingWorkflow(true);
    setWorkflowStatusError("");
    try {
      const response = normalizedWorkflowStatus === "active"
        ? await deactivateWorkflow(workflowId)
        : await activateWorkflow(workflowId);
      onWorkflowStatusChange?.(response?.status || (normalizedWorkflowStatus === "active" ? "inactive" : "active"));
      setShowWorkflowStatusConfirm(false);
    } catch (error) {
      setWorkflowStatusError(error?.message || `Unable to ${normalizedWorkflowStatus === "active" ? "deactivate" : "activate"} workflow.`);
    } finally {
      setIsTogglingWorkflow(false);
    }
  };

  return (
    <div className="relative h-12 px-4 bg-[var(--surface)] border-b border-[var(--border-subtle)] flex items-center justify-between gap-4 select-none shrink-0 font-sans z-20">
      {/* Left: Breadcrumb + version + status */}
      <div className="flex items-center gap-2.5 min-w-0">
        <button
          type="button"
          onClick={() => onNavigate?.("/workflows")}
          className="text-[13px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:underline font-medium transition-colors shrink-0"
        >
          Workflows
        </button>
        <span className="text-[13px] text-[var(--text-disabled)] font-mono">/</span>
        <div className="flex min-w-0 items-center gap-1">
          <span className="text-[13px] font-semibold text-[var(--text-primary)] truncate max-w-[200px]">
            {workflowName}
          </span>
          <button
            type="button"
            onClick={startMetadataEdit}
            aria-label="Edit workflow name and description"
            title="Edit workflow details"
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--text-tertiary)] hover:bg-[var(--elevated)] hover:text-[var(--accent)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          >
            <EditIcon className="h-3.5 w-3.5 stroke-[1.7]" />
          </button>
        </div>

        <div ref={workflowMenuRef} className="relative shrink-0">
          <button
            type="button"
            aria-label="Workflow actions"
            aria-haspopup="menu"
            aria-expanded={workflowMenuOpen}
            title="Workflow actions"
            onClick={() => setWorkflowMenuOpen((open) => !open)}
            className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-tertiary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          >
            <span aria-hidden="true" className="text-lg leading-none">⋯</span>
          </button>
          {workflowMenuOpen && (
            <div role="menu" aria-label="Workflow actions" tabIndex={-1} className="absolute left-0 top-full z-50 mt-1 w-48 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-1 text-[var(--text-primary)] shadow-xl">
              <button type="button" role="menuitem" onClick={() => { setWorkflowMenuOpen(false); startMetadataEdit(); }} className="w-full rounded-md px-2.5 py-2 text-left text-[12px] text-[var(--text-secondary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]">Edit workflow details</button>
              {isReadOnly && (
                <button type="button" role="menuitem" disabled={isCreatingDraft} onClick={() => { setWorkflowMenuOpen(false); onEditWorkflow?.(); }} className="w-full rounded-md px-2.5 py-2 text-left text-[12px] text-[var(--text-secondary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] disabled:opacity-50">Create draft version</button>
              )}
              <button type="button" role="menuitem" onClick={() => { setWorkflowMenuOpen(false); onNavigate?.("/workflows"); }} className="w-full rounded-md px-2.5 py-2 text-left text-[12px] text-[var(--text-secondary)] hover:bg-[var(--elevated)] hover:text-[var(--text-primary)]">Back to workflows</button>
              <div className="my-1 border-t border-[var(--border-subtle)]" />
              <button type="button" role="menuitem" disabled={!canDeleteWorkflow} title={!canDeleteWorkflow ? "Only draft or inactive workflows can be deleted. Deactivate active workflows first." : "Delete this workflow"} onClick={() => { setWorkflowMenuOpen(false); setDeleteWorkflowError(""); setShowDeleteConfirm(true); }} className="w-full rounded-md px-2.5 py-2 text-left text-[12px] text-red-500 hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-40">Delete workflow</button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 pl-2 border-l border-[var(--border-subtle)]">
          <WorkflowStatus status={normalizedWorkflowStatus} />
          {(normalizedWorkflowStatus === "active" || normalizedWorkflowStatus === "inactive") && (
            <span className="text-[10px] text-[var(--text-tertiary)]" title="Activation applies to the entire workflow, across all versions">All versions</span>
          )}
          {(normalizedWorkflowStatus === "active" || normalizedWorkflowStatus === "inactive") && (
            <button
              type="button"
              role="switch"
              aria-checked={normalizedWorkflowStatus === "active"}
              aria-label={`${normalizedWorkflowStatus === "active" ? "Deactivate" : "Activate"} entire workflow`}
              title="Switch applies to the entire workflow, across all versions"
              onClick={() => { setWorkflowStatusError(""); setShowWorkflowStatusConfirm(true); }}
              disabled={isTogglingWorkflow}
              className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/50 disabled:cursor-not-allowed disabled:opacity-60 ${normalizedWorkflowStatus === "active" ? "bg-[#3FB950]" : "bg-[var(--border-strong)]"}`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${normalizedWorkflowStatus === "active" ? "translate-x-[18px]" : "translate-x-0.5"}`} />
              {isTogglingWorkflow && <span className="sr-only">{normalizedWorkflowStatus === "active" ? "Deactivating" : "Activating"} workflow</span>}
            </button>
          )}
          {workflowStatusError && <span role="alert" className="max-w-48 text-[11px] text-red-500">{workflowStatusError}</span>}
        </div>

        <div ref={versionMenuRef} className="relative flex items-center gap-1.5 pl-2 border-l border-[var(--border-subtle)]">
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={versionMenuOpen}
            aria-label="Select or manage workflow versions"
            onClick={() => setVersionMenuOpen((open) => !open)}
            className={`inline-flex h-7 items-center gap-2 rounded-md border px-2.5 font-mono text-[11px] font-medium transition ${versionMenuOpen ? "border-[var(--accent)] text-[var(--text-primary)]" : "border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:bg-[var(--elevated)]"}`}
          >
            <span>v{versionNumber}</span>
            <span className="text-[var(--text-tertiary)]">·</span>
            <span className="max-w-16 truncate font-sans text-[10px] text-[var(--text-tertiary)]">{currentVersion?.status || "version"}</span>
            <span aria-hidden="true" className={`text-[var(--text-tertiary)] transition-transform ${versionMenuOpen ? "rotate-180" : ""}`}>⌄</span>
          </button>
          {versionMenuOpen && (
            <div role="menu" aria-label="Workflow versions" className="absolute left-2 top-full z-[70] mt-2 w-[292px] overflow-hidden rounded-xl border border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-primary)] shadow-2xl animate-in fade-in zoom-in-95 duration-100">
              <div className="flex items-start justify-between border-b border-[var(--border-subtle)] px-3.5 py-3">
                <div>
                  <p className="text-[12px] font-semibold">Workflow versions</p>
                  <p className="mt-0.5 text-[10px] text-[var(--text-tertiary)]">Switch versions or manage their lifecycle.</p>
                </div>
                <span className="rounded border border-[var(--border-subtle)] px-1.5 py-0.5 font-mono text-[9px] text-[var(--text-tertiary)]">{versions.length}</span>
              </div>
              <div className="max-h-72 overflow-y-auto p-1.5">
                {sortedVersions.map((item) => {
                  const number = item.version_number ?? item.version;
                  const selected = Number(number) === Number(versionNumber);
                  const status = String(item.status || "draft").toLowerCase();
                  const isPublishedVersion = Boolean(publishedVersionId && item.id && String(item.id) === String(publishedVersionId));
                  const isActivePublishedVersion = normalizedWorkflowStatus === "active" && isPublishedVersion;
                  const cannotDelete = versions.length <= 1 || isActivePublishedVersion;
                  const statusStyle = status === "published" || status === "active"
                    ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400"
                    : status === "draft"
                      ? "border-amber-500/25 bg-amber-500/5 text-amber-600 dark:text-amber-400"
                      : "border-[var(--border-subtle)] text-[var(--text-tertiary)]";
                  return (
                    <div key={item.id ?? number} className={`group flex items-center gap-1 rounded-lg p-1 ${selected ? "bg-[var(--elevated)]" : "hover:bg-[var(--elevated)]"}`}>
                      <button
                        type="button"
                        role="menuitemradio"
                        aria-checked={selected}
                        onClick={() => { onSelectVersion?.(Number(number)); setVersionMenuOpen(false); }}
                        className="flex min-w-0 flex-1 items-center gap-2.5 rounded-md px-2 py-2 text-left focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                      >
                        <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-md border font-mono text-[10px] ${selected ? "border-[var(--accent)]/40 bg-[var(--accent)]/10 text-[var(--accent)]" : "border-[var(--border-subtle)] text-[var(--text-secondary)]"}`}>v{number}</span>
                        <span className="min-w-0 flex-1">
                          <span className="flex items-center gap-1.5">
                            <span className="text-[11px] font-medium">Version {number}</span>
                            {isPublishedVersion && <span className="text-[9px] text-[var(--text-tertiary)]">Published</span>}
                          </span>
                          <span className="mt-0.5 block truncate text-[9px] text-[var(--text-tertiary)]">{item.description || (selected ? "Currently open" : "Workflow snapshot")}</span>
                        </span>
                        <span className={`rounded border px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wide ${statusStyle}`}>{status}</span>
                        {selected && <CheckIcon className="h-3.5 w-3.5 shrink-0 stroke-[2] text-[var(--accent)]" />}
                      </button>
                      <button
                        type="button"
                        aria-label={`Delete version ${number}`}
                        title={versions.length <= 1 ? "Keep at least one workflow version" : isActivePublishedVersion ? "Deactivate the workflow before deleting its active version" : `Delete version ${number}`}
                        disabled={cannotDelete || isDeletingVersion}
                        onClick={() => { setDeleteVersionError(""); setVersionToDelete(item); setVersionMenuOpen(false); }}
                        className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-[12px] text-[var(--text-tertiary)] opacity-60 transition hover:bg-red-500/10 hover:text-red-500 focus:opacity-100 focus:outline-none focus:ring-1 focus:ring-red-500/50 md:opacity-0 md:group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-25"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="h-3.5 w-3.5" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2m3 0-.9 14H5.9L5 6m4 4v6m6-6v6" strokeLinecap="round" strokeLinejoin="round" /></svg>
                      </button>
                    </div>
                  );
                })}
                {versions.length === 0 && <p className="px-3 py-5 text-center text-[11px] text-[var(--text-tertiary)]">No versions found.</p>}
              </div>
              {isReadOnly && !hasDraftVersion && (
                <div className="border-t border-[var(--border-subtle)] p-2">
                  <button type="button" disabled={isCreatingDraft} onClick={() => { setVersionMenuOpen(false); onEditWorkflow?.(); }} className="flex h-8 w-full items-center justify-center gap-2 rounded-md border border-[var(--accent)]/30 bg-[var(--accent)]/5 text-[11px] font-medium text-[var(--accent)] transition hover:bg-[var(--accent)]/10 disabled:opacity-50">
                    {isCreatingDraft ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" /> : <span aria-hidden="true">＋</span>}
                    {isCreatingDraft ? "Creating draft…" : "Create draft version"}
                  </button>
                </div>
              )}
            </div>
          )}
          {isReadOnly && (
            <span className="text-[10px] font-mono text-[var(--text-tertiary)] bg-[var(--elevated)] border border-[var(--border-subtle)] px-1.5 py-0.5 rounded-[4px]">
              READ ONLY
            </span>
          )}
        </div>
      </div>

      {editingMetadata && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/50 p-4 backdrop-blur-[2px]" onMouseDown={(event) => { if (event.target === event.currentTarget && !isSavingMetadata) setEditingMetadata(false); }}>
          <form onSubmit={saveMetadata} className="w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 shadow-2xl" aria-label="Edit workflow details">
            <div className="mb-4">
              <h2 className="text-[16px] font-semibold text-[var(--text-primary)]">Workflow details</h2>
              <p className="mt-1 text-[12px] text-[var(--text-secondary)]">Update the name and description shown across your workspace.</p>
            </div>
            <label className="mb-3 block">
              <span className="mb-1 block text-[11px] font-medium text-[var(--text-secondary)]">Name</span>
              <input maxLength={255} value={nameDraft} onChange={(event) => setNameDraft(event.target.value)} className="h-9 w-full rounded-lg border border-[var(--border-default)] bg-[var(--input-bg)] px-3 text-[13px] text-[var(--text-primary)] outline-none focus:border-[var(--accent)]" />
            </label>
            <label className="mb-3 block">
              <span className="mb-1 block text-[11px] font-medium text-[var(--text-secondary)]">Description</span>
              <textarea rows={4} value={descriptionDraft} onChange={(event) => setDescriptionDraft(event.target.value)} placeholder="What does this workflow do?" className="w-full resize-y rounded-lg border border-[var(--border-default)] bg-[var(--input-bg)] px-3 py-2 text-[13px] leading-5 text-[var(--text-primary)] outline-none focus:border-[var(--accent)]" />
            </label>
            {metadataError && <p className="mb-3 text-[12px] text-red-500">{metadataError}</p>}
            <div className="flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <button type="button" disabled={isSavingMetadata} onClick={() => setEditingMetadata(false)} className="h-8 rounded-lg border border-[var(--border-default)] px-3 text-[12px] font-medium text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-50">Cancel</button>
              <button type="submit" disabled={isSavingMetadata} className="inline-flex h-8 items-center gap-2 rounded-lg bg-[var(--accent)] px-3 text-[12px] font-medium text-white hover:opacity-90 disabled:opacity-50">
                {isSavingMetadata && <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                Save details
              </button>
            </div>
          </form>
        </div>
      )}

      {showWorkflowStatusConfirm && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/55 p-4 backdrop-blur-[2px]" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !isTogglingWorkflow) setShowWorkflowStatusConfirm(false); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="workflow-status-confirm-title" className="w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 shadow-2xl">
            <h2 id="workflow-status-confirm-title" className="text-[16px] font-semibold text-[var(--text-primary)]">
              {normalizedWorkflowStatus === "active" ? "Deactivate workflow?" : "Activate workflow?"}
            </h2>
            <p className="mt-2 text-[13px] leading-5 text-[var(--text-secondary)]">
              {normalizedWorkflowStatus === "active"
                ? "This will stop the entire workflow from running. The change applies to all versions, not only the version currently selected."
                : "This will enable the entire workflow to run. The change applies to all versions, not only the version currently selected."}
            </p>
            {workflowStatusError && <p role="alert" className="mt-3 text-[12px] text-red-500">{workflowStatusError}</p>}
            <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <button type="button" disabled={isTogglingWorkflow} onClick={() => setShowWorkflowStatusConfirm(false)} className="h-8 rounded-lg border border-[var(--border-default)] px-3 text-[12px] font-medium text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-50">Cancel</button>
              <button type="button" disabled={isTogglingWorkflow} onClick={toggleWorkflowStatus} className={`inline-flex h-8 items-center gap-2 rounded-lg px-3 text-[12px] font-medium text-white disabled:opacity-50 ${normalizedWorkflowStatus === "active" ? "bg-red-600 hover:bg-red-700" : "bg-[var(--accent)] hover:opacity-90"}`}>
                {isTogglingWorkflow && <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                {isTogglingWorkflow ? (normalizedWorkflowStatus === "active" ? "Deactivating..." : "Activating...") : (normalizedWorkflowStatus === "active" ? "Deactivate workflow" : "Activate workflow")}
              </button>
            </div>
          </section>
        </div>
      )}

      {showDeleteConfirm && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/55 p-4 backdrop-blur-[2px]" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !isDeletingWorkflow) setShowDeleteConfirm(false); }}>
          <section role="dialog" aria-modal="true" aria-labelledby="workflow-delete-confirm-title" className="w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 shadow-2xl">
            <h2 id="workflow-delete-confirm-title" className="text-[16px] font-semibold text-[var(--text-primary)]">Delete workflow?</h2>
            <p className="mt-2 text-[13px] leading-5 text-[var(--text-secondary)]">This permanently deletes <span className="font-medium text-[var(--text-primary)]">{workflowName}</span> and its versions. This cannot be undone.</p>
            {deleteWorkflowError && <p role="alert" className="mt-3 text-[12px] text-red-500">{deleteWorkflowError}</p>}
            <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <button type="button" disabled={isDeletingWorkflow} onClick={() => setShowDeleteConfirm(false)} className="h-8 rounded-lg border border-[var(--border-default)] px-3 text-[12px] font-medium text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-50">Cancel</button>
              <button type="button" disabled={isDeletingWorkflow} onClick={confirmDeleteWorkflow} className="inline-flex h-8 items-center gap-2 rounded-lg bg-red-600 px-3 text-[12px] font-medium text-white hover:bg-red-700 disabled:opacity-50">
                {isDeletingWorkflow && <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                {isDeletingWorkflow ? "Deleting..." : "Delete workflow"}
              </button>
            </div>
          </section>
        </div>
      )}

      {versionToDelete && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/55 p-4 backdrop-blur-[2px]" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !isDeletingVersion) setVersionToDelete(null); }}>
          <section role="alertdialog" aria-modal="true" aria-labelledby="workflow-version-delete-title" className="w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 shadow-2xl">
            <div className="flex items-start gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-red-500/25 bg-red-500/10 font-mono text-[15px] text-red-500">!</span>
              <div>
                <h2 id="workflow-version-delete-title" className="text-[15px] font-semibold text-[var(--text-primary)]">Delete version {versionToDelete.version_number ?? versionToDelete.version}?</h2>
                <p className="mt-1.5 text-[12px] leading-5 text-[var(--text-secondary)]">This permanently removes this version’s nodes and connections. Its webhook endpoints and credentials will also be revoked. Other versions are not affected.</p>
              </div>
            </div>
            {deleteVersionError && <p role="alert" className="mt-3 rounded-lg border border-red-500/25 bg-red-500/5 p-2.5 text-[11px] text-red-500">{deleteVersionError}</p>}
            <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <button type="button" disabled={isDeletingVersion} onClick={() => setVersionToDelete(null)} className="h-8 rounded-lg border border-[var(--border-default)] px-3 text-[11px] font-medium text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-50">Cancel</button>
              <button type="button" disabled={isDeletingVersion} onClick={confirmDeleteVersion} className="inline-flex h-8 items-center gap-2 rounded-lg bg-red-600 px-3 text-[11px] font-medium text-white hover:bg-red-700 disabled:opacity-50">
                {isDeletingVersion && <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                {isDeletingVersion ? "Deleting version…" : "Delete version"}
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Right: Save indicator + actions */}
      <div className="flex items-center gap-3 shrink-0">
        {!isReadOnly && (
          <div className="flex items-center gap-1 border-r border-[var(--border-subtle)] pr-2">
            <button type="button" onClick={onUndo} disabled={!canUndo} title="Undo (Ctrl/Cmd+Z)" aria-label="Undo" className="h-8 w-8 rounded-[6px] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-35 disabled:cursor-not-allowed">↶</button>
            <button type="button" onClick={onRedo} disabled={!canRedo} title="Redo (Ctrl/Cmd+Shift+Z)" aria-label="Redo" className="h-8 w-8 rounded-[6px] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-35 disabled:cursor-not-allowed">↷</button>
          </div>
        )}
        {/* Save state indicator */}
        <div className="flex items-center gap-1.5 text-[12px] text-[var(--text-tertiary)] font-mono pr-2">
          {saveState === "saving" && (
            <>
              <div className="w-3 h-3 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
              <span>Saving...</span>
            </>
          )}
          {saveState === "unsaved" && (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-[#D29922] animate-pulse" />
              <span className="text-[#D29922]">{saveError ?? "Unsaved changes"}</span>
            </>
          )}
          {saveState === "failed" && (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-[#F85149]" />
              <span className="text-[#F85149]">{saveError ?? "Save failed"}</span>
            </>
          )}
          {saveState === "saved" && !isReadOnly && (
            <>
              <CheckIcon className="w-3.5 h-3.5 text-[#3FB950] stroke-[2]" />
              <span>Saved</span>
            </>
          )}
        </div>

        {/* Save button (draft only) */}
        {!isReadOnly && (
          <button
            type="button"
            onClick={onSave}
            disabled={saveState === "saving"}
            className="h-8 px-3 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[12px] font-medium text-[var(--text-primary)] transition-all duration-100 ease-out flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {saveState === "saving" ? (
              <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : saveState === "failed" ? (
              <RefreshCwIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            ) : (
              <SaveIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            )}
            <span>{saveState === "failed" ? "Retry" : "Save"}</span>
          </button>
        )}

        {/* Edit Workflow (published mode) */}
        {isReadOnly && (
          <button
            type="button"
            onClick={onEditWorkflow}
            disabled={isCreatingDraft}
            className="h-8 px-3 rounded-[6px] border border-[var(--accent)] bg-[var(--accent)]/10 hover:bg-[var(--accent)]/20 text-[12px] font-medium text-[var(--accent)] transition-all duration-100 ease-out flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Create a new draft version to edit"
          >
            {isCreatingDraft ? (
              <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <EditIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            )}
            <span>{isCreatingDraft ? "Creating draft..." : "Edit Workflow"}</span>
          </button>
        )}

        {/* Validate */}
        <button
          type="button"
          onClick={onValidate}
          disabled={isValidating}
          className="h-8 px-3 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[12px] font-medium text-[var(--text-primary)] transition-all duration-100 ease-out flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
        >
          {isValidating ? (
            <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
          ) : (
            <ShieldCheckIcon className="w-3.5 h-3.5 stroke-[1.5]" />
          )}
          <span>Validate</span>
        </button>

        {/* Publish (draft only) */}
        {!isReadOnly && (
          <button
            type="button"
            onClick={onPublish}
            disabled={isPublishing}
            className="h-8 px-3.5 rounded-[6px] bg-[#4F46E5] hover:bg-[#6366F1] active:opacity-90 text-white font-medium text-[12px] transition-all duration-100 ease-out flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {isPublishing ? (
              <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <RocketIcon className="w-3.5 h-3.5 stroke-[1.5]" />
            )}
            <span>Publish</span>
          </button>
        )}
      </div>
    </div>
  );
}
