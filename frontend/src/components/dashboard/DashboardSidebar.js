"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import SidebarNavItem from "./SidebarNavItem";
import ProfileMenu from "./ProfileMenu";

// SVG Line Icons (1.5px stroke)
function DashboardIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <rect width="7" height="7" x="3" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="3" rx="1" />
      <rect width="7" height="7" x="14" y="14" rx="1" />
      <rect width="7" height="7" x="3" y="14" rx="1" />
    </svg>
  );
}

function WorkflowsIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="18" r="3" />
      <path d="M18 6a3 3 0 0 0-3 3v6a3 3 0 0 1-3 3H9" />
    </svg>
  );
}

function ExecutionsIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="10" />
      <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ConnectionsIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M12 2v8" />
      <path d="m16 6-4 4-4-4" />
      <rect width="16" height="8" x="4" y="14" rx="2" />
      <path d="M6 18h.01" />
      <path d="M10 18h.01" />
    </svg>
  );
}

function KnowledgeBasesIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
    </svg>
  );
}

function PanelToggleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M9 3v18" />
      <path d="m14 9 3 3-3 3" />
    </svg>
  );
}

export default function DashboardSidebar({
  isCollapsed,
  onToggleCollapse,
  mobileOpen,
  onMobileClose,
}) {
  const pathname = usePathname();
  const { user } = useAuth();

  const userName = user?.name || user?.email?.split("@")[0] || "Shaad";
  const userInitial = userName.charAt(0).toUpperCase();

  const mainNavItems = [
    { label: "Dashboard", href: "/dashboard", icon: DashboardIcon },
    { label: "Workflows", href: "/dashboard/workflows", icon: WorkflowsIcon },
    { label: "Executions", href: "/dashboard/executions", icon: ExecutionsIcon },
  ];

  const resourceNavItems = [
    { label: "Connections", href: "/dashboard/connections", icon: ConnectionsIcon },
    { label: "Knowledge Bases", href: "/dashboard/knowledge-bases", icon: KnowledgeBasesIcon },
  ];

  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[var(--surface)] border-r border-[var(--border-subtle)] transition-all duration-150 ease-out select-none overflow-hidden">
      {/* Brand Header */}
      <div className={`h-14 flex items-center ${isCollapsed ? "justify-center px-2" : "justify-between px-4"} border-b border-[var(--border-subtle)] shrink-0`}>
        {!isCollapsed ? (
          <>
            <Link href="/dashboard" className="flex items-center gap-3 overflow-hidden">
              <Image
                src="/brand/relay/relay-dark.png"
                alt="Relay Logo"
                width={160}
                height={48}
                priority
                className="w-auto h-9 dark:hidden object-contain"
              />
              <Image
                src="/brand/relay/relay-light.png"
                alt="Relay Logo"
                width={160}
                height={48}
                priority
                className="w-auto h-9 hidden dark:block object-contain"
              />
            </Link>

            {/* Desktop Sidebar Collapse Toggle */}
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label="Collapse sidebar"
              className="hidden md:flex p-1.5 rounded-[6px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 cursor-pointer"
            >
              <PanelToggleIcon className="w-4 h-4 stroke-[1.5]" />
            </button>
          </>
        ) : (
          /* When Collapsed: Maximize/Expand Icon Button at Top */
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label="Expand sidebar"
            className="w-8 h-8 rounded-[6px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 cursor-pointer"
          >
            <PanelToggleIcon className="w-4 h-4 stroke-[1.5] rotate-180" />
          </button>
        )}
      </div>

      {/* Navigation Links Area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-2.5 py-4 space-y-6">
        {/* Main Group */}
        <div>
          {!isCollapsed && (
            <div className="px-3 mb-2 text-[10px] font-mono tracking-wider text-[var(--text-tertiary)] uppercase">
              Main
            </div>
          )}
          <nav aria-label="Main Navigation" className="space-y-1">
            {mainNavItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <SidebarNavItem
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={isActive}
                  collapsed={isCollapsed}
                  onClick={onMobileClose}
                />
              );
            })}
          </nav>
        </div>

        {/* Resources Group */}
        <div>
          {!isCollapsed && (
            <div className="px-3 mb-2 text-[10px] font-mono tracking-wider text-[var(--text-tertiary)] uppercase">
              Resources
            </div>
          )}
          <nav aria-label="Resource Navigation" className="space-y-1">
            {resourceNavItems.map((item) => {
              const isActive = pathname.startsWith(item.href);
              return (
                <SidebarNavItem
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={isActive}
                  collapsed={isCollapsed}
                  onClick={onMobileClose}
                />
              );
            })}
          </nav>
        </div>
      </div>

      {/* Bottom User / Workspace Section */}
      <div className="relative p-2 border-t border-[var(--border-subtle)] shrink-0">
        <button
          type="button"
          aria-expanded={profileMenuOpen}
          aria-haspopup="true"
          onClick={() => setProfileMenuOpen((prev) => !prev)}
          aria-label="User profile menu"
          className={`w-full flex items-center ${
            isCollapsed ? "justify-center p-1.5" : "gap-3 p-1.5 text-left"
          } rounded-[6px] hover:bg-[var(--elevated)] transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--accent)]/40`}
        >
          {/* User Avatar */}
          <div className="w-8 h-8 rounded-[6px] bg-[var(--elevated)] border border-[var(--border-default)] flex items-center justify-center font-bold text-[13px] text-[var(--text-primary)] shrink-0">
            {userInitial}
          </div>

          {/* User Info (Expanded only) */}
          {!isCollapsed && (
            <div className="min-w-0 flex-1">
              <div className="text-[13px] font-medium text-[var(--text-primary)] truncate leading-tight">
                {userName}
              </div>
              <div className="text-[11px] text-[var(--text-tertiary)] truncate mt-0.5">
                Workspace
              </div>
            </div>
          )}
        </button>

        {/* Profile Popover Menu */}
        <ProfileMenu
          open={profileMenuOpen}
          onClose={() => setProfileMenuOpen(false)}
          positionClass="bottom-full mb-2 left-2 w-64"
        />
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Full-Height Sticky 240px / 64px) */}
      <aside
        className={`hidden md:flex flex-col h-screen sticky top-0 z-40 shrink-0 transition-all duration-150 ease-out ${
          isCollapsed ? "w-[64px]" : "w-[240px]"
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer (Responsive Overlay) */}
      {mobileOpen && (
        <div className="md:hidden">
          {/* Backdrop Overlay */}
          <div
            className="fixed inset-0 bg-black/60 z-40 backdrop-blur-xs transition-opacity"
            onClick={onMobileClose}
            aria-hidden="true"
          />

          {/* Drawer Container */}
          <div className="fixed inset-y-0 left-0 w-[240px] z-50 shadow-xl animate-in slide-in-from-left duration-150">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
