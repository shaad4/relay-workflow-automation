"use client";

function SearchIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export default function WorkflowSearchEmptyState({ query = "", onClearSearch }) {
  return (
    <div className="w-full bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl p-8 sm:p-12 text-center my-4 select-none">
      <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-4 text-[var(--text-tertiary)]">
        <SearchIcon className="w-6 h-6 stroke-[1.5]" />
      </div>

      <h3 className="text-[16px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
        No workflows found
      </h3>

      <p className="text-[14px] text-[var(--text-secondary)] max-w-sm mx-auto mb-5 leading-relaxed">
        {query ? (
          <>
            No workflows matching &quot;<span className="text-[var(--text-primary)] font-medium">{query}</span>&quot;.
          </>
        ) : (
          "Try a different search term."
        )}
      </p>

      {onClearSearch && (
        <button
          type="button"
          onClick={onClearSearch}
          className="inline-flex items-center h-8 px-3 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] text-[13px] font-medium text-[var(--text-primary)] transition-all duration-100 ease-out focus:outline-none focus:ring-1 focus:ring-[var(--accent)] cursor-pointer"
        >
          Clear search
        </button>
      )}
    </div>
  );
}
