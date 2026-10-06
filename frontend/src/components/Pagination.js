"use client";

export default function Pagination({ page, pageSize, total, onPageChange }) {
  const pageCount = Math.ceil(total / pageSize);
  if (pageCount <= 1) return null;

  const firstItem = (page - 1) * pageSize + 1;
  const lastItem = Math.min(page * pageSize, total);
  const buttonClass = "h-8 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] px-2.5 text-[12px] font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] disabled:pointer-events-none disabled:opacity-40";

  return (
    <nav aria-label="Pagination" className="flex items-center justify-between gap-3 border-t border-[var(--border-subtle)] pt-3">
      <p className="text-[11px] tabular-nums text-[var(--text-tertiary)]">
        {firstItem}–{lastItem} <span className="text-[var(--text-disabled)]">of</span> {total}
      </p>
      <div className="flex items-center gap-2">
        <button type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)} className={buttonClass}>
          Previous
        </button>
        <span aria-live="polite" className="min-w-14 text-center text-[11px] tabular-nums text-[var(--text-tertiary)]">
          {page} <span className="text-[var(--text-disabled)]">/</span> {pageCount}
        </span>
        <button type="button" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)} className={buttonClass}>
          Next
        </button>
      </div>
    </nav>
  );
}
