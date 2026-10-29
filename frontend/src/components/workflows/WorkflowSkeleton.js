"use client";

export default function WorkflowSkeleton() {
  return (
    <div
      className="grid w-full grid-cols-1 gap-3.5 animate-pulse select-none md:grid-cols-2 xl:grid-cols-3"
      aria-label="Loading workflows"
      role="status"
    >
      {[1, 2, 3, 4, 5, 6].map((item) => (
        <div
          key={item}
          className="flex min-h-[216px] flex-col rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 shadow-sm"
        >
          <div className="flex items-start gap-3">
            <div className="h-11 w-11 shrink-0 rounded-xl border border-[var(--border-subtle)] bg-[var(--elevated)]" />
            <div className="min-w-0 flex-1 space-y-2 pt-1">
              <div className="h-4 w-3/5 rounded bg-[var(--elevated)]" />
              <div className="h-2.5 w-2/5 rounded bg-[var(--elevated)]/70" />
            </div>
            <div className="h-6 w-6 rounded-md bg-[var(--elevated)]/70" />
          </div>

          <div className="mt-5 space-y-2">
            <div className="h-3 w-full rounded bg-[var(--elevated)]/80" />
            <div className="h-3 w-11/12 rounded bg-[var(--elevated)]/70" />
            <div className="h-3 w-3/5 rounded bg-[var(--elevated)]/60" />
          </div>

          <div className="mt-auto flex items-center justify-between gap-3 border-t border-[var(--border-subtle)] pt-3">
            <div className="h-3.5 w-16 rounded bg-[var(--elevated)]" />
            <div className="h-3 w-24 rounded bg-[var(--elevated)]/70" />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading workflows…</span>
    </div>
  );
}
