"use client";

import Link from "next/link";

export default function SidebarNavItem({
  href,
  label,
  icon: Icon,
  active = false,
  collapsed = false,
  badgeCount,
  onClick,
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      title={collapsed ? `${label}${badgeCount > 0 ? ` (${badgeCount} pending)` : ""}` : undefined}
      className={`group relative flex items-center overflow-hidden ${
        collapsed ? "justify-center p-2" : "gap-3 px-3 py-2"
      } text-[13px] font-medium rounded-[7px] transition-colors duration-150 ease-out select-none ${
        active
          ? "bg-[var(--elevated)] text-[var(--text-primary)]"
          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)]/70"
      }`}
    >
      {active && <span aria-hidden="true" className="absolute inset-y-2 left-0 w-0.5 rounded-r-full bg-[var(--text-primary)]"/>}
      {/* Icon */}
      <div className="shrink-0 flex items-center justify-center w-5 h-5 text-current">
        <Icon className="w-4 h-4 stroke-[1.5]" />
      </div>

      {/* Label */}
      {!collapsed && <span className="min-w-0 flex-1 truncate text-left">{label}</span>}

      {badgeCount > 0 && !collapsed && <span aria-label={`${badgeCount} pending approvals`} className="ml-auto inline-flex min-w-5 h-5 items-center justify-center rounded-full bg-[var(--accent)]/10 px-1.5 text-[10px] font-semibold tabular-nums text-[var(--accent)]">{badgeCount > 99 ? "99+" : badgeCount}</span>}
      {badgeCount > 0 && collapsed && <span aria-label={`${badgeCount} pending approvals`} className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[var(--accent)] ring-2 ring-[var(--surface)]"/>}

      {/* Hover Tooltip when Collapsed */}
      {collapsed && (
        <div className="hidden md:block pointer-events-none absolute left-full ml-2 px-2.5 py-1 bg-[var(--elevated)] border border-[var(--border-default)] text-[var(--text-primary)] text-[12px] font-medium rounded-[6px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50 shadow-sm">
          {label}{badgeCount > 0 ? ` · ${badgeCount} pending` : ""}
        </div>
      )}
    </Link>
  );
}
