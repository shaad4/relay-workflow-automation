"use client";

import Link from "next/link";
import WorkflowStatus from "../workflows/WorkflowStatus";

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
  versionNumber = 1,
  versions = [],
  onSelectVersion,
  updatedAt,
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
  return (
    <div className="h-12 px-4 bg-[var(--surface)] border-b border-[var(--border-subtle)] flex items-center justify-between gap-4 select-none shrink-0 font-sans z-10">
      {/* Left: Breadcrumb + version + status */}
      <div className="flex items-center gap-2.5 min-w-0">
        <Link
          href="/workflows"
          className="text-[13px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:underline font-medium transition-colors shrink-0"
        >
          Workflows
        </Link>
        <span className="text-[13px] text-[var(--text-disabled)] font-mono">/</span>
        <span className="text-[13px] font-semibold text-[var(--text-primary)] truncate max-w-[200px]">
          {workflowName}
        </span>

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
        <span className="hidden xl:inline text-[10px] text-[var(--text-tertiary)] border-l border-[var(--border-subtle)] pl-2">
          Last saved {updatedAt ? new Date(updatedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "Not saved yet"}
        </span>
      </div>

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
