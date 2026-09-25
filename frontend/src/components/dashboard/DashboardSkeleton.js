export default function DashboardSkeleton() {
  return (
    <div className="space-y-8 select-none">
      {/* Top Header Section */}
      <div>
        <h1 className="text-[24px] sm:text-[28px] font-bold text-[var(--text-primary)] tracking-tight">
          Dashboard
        </h1>
        <p className="text-[14px] text-[var(--text-secondary)] mt-1">
          Overview of your automation workspace.
        </p>
      </div>

      {/* 1. Statistics Cards Skeleton Grid (4 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((index) => (
          <div
            key={index}
            className="bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl p-5"
          >
            {/* Small Label Skeleton */}
            <div className="h-3.5 w-24 bg-[var(--elevated)] rounded animate-pulse" />
            {/* Large Number Skeleton */}
            <div className="h-7 w-20 bg-[var(--elevated)] rounded mt-3.5 animate-pulse" />
            {/* Small Secondary Line Skeleton */}
            <div className="h-3 w-32 bg-[var(--elevated)] rounded mt-2.5 opacity-60 animate-pulse" />
          </div>
        ))}
      </div>

      {/* 2. Main Content Skeleton Panel */}
      <div className="bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl p-6 space-y-4">
        {/* Panel Header */}
        <div className="flex items-center justify-between pb-2 border-b border-[var(--border-subtle)]">
          <div className="h-5 w-44 bg-[var(--elevated)] rounded animate-pulse" />
          <div className="h-4 w-20 bg-[var(--elevated)] rounded opacity-60 animate-pulse" />
        </div>

        {/* List / Table Rows Skeleton */}
        <div className="space-y-3 pt-2">
          {[1, 2, 3, 4, 5].map((row) => (
            <div
              key={row}
              className="h-10 w-full bg-[var(--elevated)] rounded-[6px] opacity-70 animate-pulse flex items-center justify-between px-4"
            >
              <div className="h-3.5 w-1/3 bg-[var(--surface)] rounded opacity-60" />
              <div className="h-3.5 w-16 bg-[var(--surface)] rounded opacity-60" />
            </div>
          ))}
        </div>
      </div>

      {/* 3. Secondary Content Skeleton Panels (2 Cards) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2].map((panel) => (
          <div
            key={panel}
            className="bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl p-6 space-y-4"
          >
            {/* Card Header */}
            <div className="h-5 w-36 bg-[var(--elevated)] rounded animate-pulse" />

            {/* Content Lines */}
            <div className="space-y-2.5 pt-1">
              <div className="h-4 w-full bg-[var(--elevated)] rounded opacity-60 animate-pulse" />
              <div className="h-4 w-4/5 bg-[var(--elevated)] rounded opacity-60 animate-pulse" />
              <div className="h-4 w-2/3 bg-[var(--elevated)] rounded opacity-60 animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
