"use client";

export default function WorkflowSkeleton() {
  return (
    <div className="w-full space-y-4 animate-pulse select-none">
      {/* Table Container Skeleton */}
      <div className="w-full bg-[var(--surface)] border border-[var(--border-subtle)] rounded-lg overflow-hidden">
        {/* Table Header Skeleton */}
        <div className="hidden sm:flex items-center justify-between gap-4 h-9 px-4 border-b border-[var(--border-subtle)] bg-[var(--elevated)]/60">
          <div className="w-20 h-3 bg-[var(--border-default)] rounded-[3px]" />
          <div className="flex items-center justify-end gap-5 sm:gap-6 shrink-0">
            <div className="w-24 h-3 bg-[var(--border-default)] rounded-[3px]" />
            <div className="w-24 h-3 bg-[var(--border-default)] rounded-[3px] hidden md:block" />
            <div className="w-28 h-3 bg-[var(--border-default)] rounded-[3px] hidden lg:block" />
            <div className="w-16 h-3 bg-[var(--border-default)] rounded-[3px]" />
          </div>
        </div>

        {/* Skeleton Rows */}
        <div className="divide-y divide-[var(--border-subtle)]">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="px-4 py-3 flex items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1 min-w-0">
                <div className="w-44 sm:w-60 h-3.5 bg-[var(--elevated)] rounded-[3px]" />
                <div className="w-32 sm:w-72 h-3 bg-[var(--elevated)]/50 rounded-[3px]" />
              </div>

              <div className="flex items-center justify-end gap-5 sm:gap-6 shrink-0">
                <div className="w-24 h-3.5 bg-[var(--elevated)] rounded-[3px]" />
                <div className="w-24 h-3 bg-[var(--elevated)]/50 rounded-[3px] hidden md:block" />
                <div className="w-28 h-3 bg-[var(--elevated)]/50 rounded-[3px] hidden lg:block" />
                <div className="w-16 flex justify-end">
                  <div className="w-6 h-6 rounded-[4px] bg-[var(--elevated)]/40" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
