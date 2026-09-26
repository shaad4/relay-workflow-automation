"use client";

function AlertTriangleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function RefreshIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M21.5 2v6h-6" />
      <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
    </svg>
  );
}

export default function WorkflowErrorState({ errorMessage = "", onRetry }) {
  return (
    <div className="w-full bg-[var(--surface)] border border-red-500/20 rounded-xl p-8 sm:p-12 text-center my-4 select-none">
      <div className="mx-auto w-12 h-12 rounded-[8px] bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4 text-[#F85149]">
        <AlertTriangleIcon className="w-6 h-6 stroke-[1.5]" />
      </div>

      <h3 className="text-[16px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
        Unable to load workflows
      </h3>

      <p className="text-[14px] text-[var(--text-secondary)] max-w-sm mx-auto mb-6 leading-relaxed">
        {errorMessage || "Something went wrong while loading your workflows."}
      </p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 h-9 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[14px] font-medium text-[var(--text-primary)] transition-all duration-100 ease-out focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 cursor-pointer"
        >
          <RefreshIcon className="w-4 h-4 stroke-[1.5]" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}
