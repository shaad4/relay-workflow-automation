"use client";

import { useState } from "react";
import WorkflowStatus from "../workflows/WorkflowStatus";
import { updateWorkflow } from "@/services/workflows";

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
  workflowDescription = "",
  workflowId,
  token,
  onWorkflowUpdated,
  onNavigate,
  versionNumber = 1,
  versions = [],
  onSelectVersion,
  status = "draft",
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
      await updateWorkflow(token, workflowId, {
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

  return (
    <div className="h-12 px-4 bg-[var(--surface)] border-b border-[var(--border-subtle)] flex items-center justify-between gap-4 select-none shrink-0 font-sans z-10">
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

        <div className="flex items-center gap-1.5 pl-2 border-l border-[var(--border-subtle)]">
          <label className="relative flex items-center">
            <select
              value={versionNumber}
              onChange={(event) => onSelectVersion?.(Number(event.target.value))}
              className="appearance-none text-[11px] font-mono font-medium text-[var(--text-secondary)] bg-[var(--elevated)] pl-2 pr-6 py-1 rounded-[4px] border border-[var(--border-subtle)] cursor-pointer focus:outline-none focus:border-[var(--accent)]"
              aria-label="Select workflow version"
            >
              {[...versions].sort((a, b) => Number(b.version_number ?? b.version) - Number(a.version_number ?? a.version)).map((item) => {
                const number = item.version_number ?? item.version;
                return <option key={item.id ?? number} value={number}>v{number} · {item.status}</option>;
              })}
              {versions.length === 0 && <option value={versionNumber}>v{versionNumber}</option>}
            </select>
            <span className="pointer-events-none absolute right-2 text-[var(--text-tertiary)]">⌄</span>
          </label>
          <WorkflowStatus status={status} />
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
              <input autoFocus maxLength={255} value={nameDraft} onChange={(event) => setNameDraft(event.target.value)} className="h-9 w-full rounded-lg border border-[var(--border-default)] bg-[var(--input-bg)] px-3 text-[13px] text-[var(--text-primary)] outline-none focus:border-[var(--accent)]" />
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
