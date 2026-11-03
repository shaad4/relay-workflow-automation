"use client";

import ValidationIssue from "./ValidationIssue";

export default function WorkflowValidation({
  open,
  isValid,
  errors = [],
  warnings = [],
  onClose,
  onSelectIssue,
  sampleText = "",
  onSampleChange,
  onValidate,
  isValidating = false,
  needsValidation = false,
}) {
  if (!open) return null;
  const title = isValidating
    ? "Validating workflow…"
    : needsValidation
      ? "Validate sample input"
      : isValid
        ? "Workflow valid"
        : "Validation issues";
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="workflow-validation-title"
        aria-busy={isValidating}
        className="w-full max-w-lg space-y-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface)] p-6 shadow-xl"
      >
        <div className="flex items-center justify-between gap-3">
          <h2
            id="workflow-validation-title"
            className="text-[16px] font-semibold text-[var(--text-primary)]"
          >
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close validation"
            className="text-[var(--text-secondary)]"
          >
            ×
          </button>
        </div>
        <p role="status" className="text-[12px] text-[var(--text-secondary)]">
          {isValidating
            ? "Checking the current canvas."
            : needsValidation
              ? "Validate again to check the updated sample."
              : isValid
                ? "The current canvas passed validation. Unsaved changes have not been saved."
                : "Fix these issues before publishing. Select a node issue to open its settings."}
        </p>
        {!isValidating && !needsValidation && (
          <div className="max-h-64 space-y-3 overflow-y-auto">
            {errors.map((issue, index) => (
              <div
                key={index}
                className="rounded-md border border-red-500/25 bg-red-500/5 p-3 text-red-600 dark:text-red-400"
              >
                <ValidationIssue issue={issue} onSelect={onSelectIssue} />
              </div>
            ))}
            {warnings.map((issue, index) => (
              <div
                key={index}
                className="rounded-md border border-amber-500/25 p-3 text-amber-600 dark:text-amber-400"
              >
                <span className="text-[10px] font-semibold">Warning</span>
                <ValidationIssue issue={issue} onSelect={onSelectIssue} />
              </div>
            ))}
          </div>
        )}
        {onSampleChange && (
          <div className="space-y-1">
            <label
              htmlFor="validation-sample"
              className="text-[12px] font-medium text-[var(--text-primary)]"
            >
              Sample trigger input (optional)
            </label>
            <textarea
              id="validation-sample"
              value={sampleText}
              onChange={(event) => onSampleChange(event.target.value)}
              rows={3}
              placeholder={'{"research_topic": "How RAG works"}'}
              className="w-full rounded-md border border-[var(--border-default)] bg-[var(--input-bg)] p-2 font-mono text-[11px] text-[var(--text-primary)]"
            />
            <p className="text-[11px] text-[var(--text-tertiary)]">
              Enter the object available at trigger.data. Leave blank to check
              the workflow without sample input. This does not run the workflow.
            </p>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-[12px] text-[var(--text-primary)]"
          >
            Close
          </button>
          {onValidate && (
            <button
              type="button"
              onClick={onValidate}
              disabled={isValidating}
              className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-[12px] text-white disabled:opacity-50"
            >
              Validate again
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
