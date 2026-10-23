"use client";

import Link from "next/link";

export default function SidebarNavItem({
  href,
  label,
  icon: Icon,
  active = false,
  collapsed = false,
  badgeCount,
  badgeLabel = "items needing attention",
  onClick,
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      title={collapsed ? `${label}${badgeCount > 0 ? ` (${badgeCount} ${badgeLabel})` : ""}` : undefined}
      className={`relay-sidebar-link group relative flex items-center ${
        collapsed ? "justify-center p-2" : "gap-3 px-3 py-2"
      } text-[13px] font-medium rounded-[7px] transition-colors duration-150 ease-out select-none ${
        active
          ? "bg-[var(--elevated)] text-[var(--text-primary)]"
          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)]/70"
      }`}
    >
      {/* Icon */}
      <div className="shrink-0 flex items-center justify-center w-5 h-5 text-current">
        <Icon className="w-4 h-4 stroke-[1.5]" />
      </div>

      {/* Label */}
      {!collapsed && <span className="min-w-0 flex-1 truncate text-left">{label}</span>}

      {badgeCount > 0 && !collapsed && <span aria-label={`${badgeCount} ${badgeLabel}`} className="sidebar-attention-badge">{badgeCount > 99 ? "99+" : badgeCount}</span>}
      {badgeCount > 0 && collapsed && <span aria-label={`${badgeCount} ${badgeLabel}`} className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[var(--text-secondary)] ring-2 ring-[var(--surface)]"/>}

      {/* Hover Tooltip when Collapsed */}
      {collapsed && (
        <div className="hidden md:block pointer-events-none absolute left-full ml-2 px-2.5 py-1 bg-[var(--elevated)] border border-[var(--border-default)] text-[var(--text-primary)] text-[12px] font-medium rounded-[6px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50 shadow-sm">
          {label}{badgeCount > 0 ? ` · ${badgeCount} ${badgeLabel}` : ""}
        </div>
      )}
    </Link>
  );
}
