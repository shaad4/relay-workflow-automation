"use client";

import Link from "next/link";

export default function SidebarNavItem({
  href,
  label,
  icon: Icon,
  active = false,
  collapsed = false,
  onClick,
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      title={collapsed ? label : undefined}
      className={`group relative flex items-center ${
        collapsed ? "justify-center p-2" : "gap-3 px-3 py-2"
      } text-[13px] font-medium rounded-[6px] transition-all duration-150 ease-out select-none ${
        active
          ? "bg-[var(--elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)]"
          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] border border-transparent"
      }`}
    >
      {/* Icon */}
      <div className="shrink-0 flex items-center justify-center w-5 h-5 text-current">
        <Icon className="w-4 h-4 stroke-[1.5]" />
      </div>

      {/* Label */}
      {!collapsed && <span className="truncate text-left">{label}</span>}

      {/* Hover Tooltip when Collapsed */}
      {collapsed && (
        <div className="hidden md:block pointer-events-none absolute left-full ml-2 px-2.5 py-1 bg-[var(--elevated)] border border-[var(--border-default)] text-[var(--text-primary)] text-[12px] font-medium rounded-[6px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-50 shadow-sm">
          {label}
        </div>
      )}
    </Link>
  );
}
