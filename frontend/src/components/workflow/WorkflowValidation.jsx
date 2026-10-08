"use client";

function CheckCircleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function AlertTriangleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function XIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

export default function WorkflowValidation({
  open,
  isValid,
  errors = [],
  onClose,
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-100 font-sans">
      <div className="w-full max-w-md bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl p-6 shadow-xl text-left select-none relative">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <XIcon className="w-4 h-4 stroke-[1.5]" />
        </button>

        {isValid ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-[8px] bg-green-500/10 border border-green-500/20 flex items-center justify-center text-[#3FB950] shrink-0">
                <CheckCircleIcon className="w-5 h-5 stroke-[1.5]" />
              </div>
              <div>
                <h3 className="text-[16px] font-semibold text-[var(--text-primary)] leading-snug">
                  Workflow Valid
                </h3>
                <p className="text-[13px] text-[var(--text-secondary)] mt-0.5">
                  Workflow is valid and ready for publishing.
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-[var(--border-subtle)] flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="h-8 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[13px] hover:bg-black dark:hover:bg-white transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-[8px] bg-red-500/10 border border-red-500/20 flex items-center justify-center text-[#F85149] shrink-0">
                <AlertTriangleIcon className="w-5 h-5 stroke-[1.5]" />
              </div>
              <div>
                <h3 className="text-[16px] font-semibold text-[var(--text-primary)] leading-snug">
                  Validation Errors
                </h3>
                <p className="text-[13px] text-[var(--text-secondary)] mt-0.5">
                  Please fix the following issues before publishing:
                </p>
              </div>
            </div>

            <div className="p-3 bg-[var(--canvas)] border border-[var(--border-subtle)] rounded-lg max-h-48 overflow-y-auto space-y-2">
              {errors.length > 0 ? (
                errors.map((err, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-[12px] text-red-500 dark:text-red-400">
                    <span className="font-mono text-[10px] bg-red-500/10 px-1 py-0.5 rounded border border-red-500/20 shrink-0">
                      {err.code || "ERR"}
                    </span>
                    <span className="leading-snug">{err.message || String(err)}</span>
                  </div>
                ))
              ) : (
                <div className="text-[12px] text-red-500 dark:text-red-400">
                  Workflow must contain at least one trigger node and one connected action.
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-[var(--border-subtle)] flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="h-8 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] text-[12px] font-medium text-[var(--text-primary)] transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
