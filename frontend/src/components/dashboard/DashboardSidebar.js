"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import SidebarNavItem from "./SidebarNavItem";
import ProfileMenu from "./ProfileMenu";
import { getExecutionGroups } from "@/services/executions";
import { getApprovals } from "@/services/approvals";

import { getDeadLetterEvents } from "@/services/deadLetter";

// Retain snapshots across sidebar remounts; isolate counts by account/workspace.
const emptyCounts = { approvals: 0, dlq: 0, executions: 0 };
const countCache = new Map();
const countRequests = new Map();
const countListeners = new Set();
function subscribeCounts(listener) { countListeners.add(listener); return () => countListeners.delete(listener); }
async function loadCounts(key) {
  if (countRequests.has(key)) return countRequests.get(key);
  const request = (async () => {
    const results = await Promise.allSettled([getApprovals(), getDeadLetterEvents({ status: "pending", limit: 1 }), getExecutionGroups({ pageSize: 1 })]);
    const previous = countCache.get(key)?.counts || emptyCounts;
    const next = { ...previous };
    if (results[0].status === "fulfilled") {
      const response = results[0].value;
      const approvals = Array.isArray(response) ? response : response?.approvals || [];
      next.approvals = approvals.filter(item => String(item.status || "pending").toLowerCase() === "pending").length;
    }
    if (results[1].status === "fulfilled" && Number.isFinite(results[1].value.total)) next.dlq = results[1].value.total;
    if (results[2].status === "fulfilled") next.executions = results[2].value.total;
    const unchanged = Object.keys(next).every(field => next[field] === previous[field]);
    countCache.set(key, { counts: unchanged ? previous : next, updated: Date.now() });
    countListeners.forEach(listener => listener());
  })().finally(() => countRequests.delete(key));
  countRequests.set(key, request);
  return request;
}

// A consistent rounded outline icon set for navigation.
function NavIcon({ children, ...props }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{children}</svg>;
}
function DashboardIcon(props) { return <NavIcon {...props}><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="11" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="18" width="7" height="3" rx="1"/></NavIcon>; }
function WorkflowsIcon(props) { return <NavIcon {...props}><rect x="3" y="8" width="6" height="7" rx="2"/><rect x="15" y="3" width="6" height="6" rx="2"/><rect x="15" y="15" width="6" height="6" rx="2"/><path d="M9 11.5h3V6h3m-3 5.5V18h3"/></NavIcon>; }
function ExecutionsIcon(props) { return <NavIcon {...props}><path d="M3 12h4l3-8 4 16 3-8h4"/></NavIcon>; }
function ApprovalsIcon(props) { return <NavIcon {...props}><rect x="5" y="5" width="14" height="16" rx="2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="m9 14 2 2 4-5"/></NavIcon>; }
function ConnectionsIcon(props) { return <NavIcon {...props}><path d="m8 12 4 4m-7-1 4 4m-2-2-4 4m14-14 4-4M14 5l5 5M8 8l8 8-3 3a5.7 5.7 0 0 1-8-8Zm3-3 2-2m3 7 2-2"/></NavIcon>; }
function KnowledgeBasesIcon(props) { return <NavIcon {...props}><path d="M12 5v16M3 3h5a4 4 0 0 1 4 2 4 4 0 0 1 4-2h5v16h-5a4 4 0 0 0-4 2 4 4 0 0 0-4-2H3Z"/></NavIcon>; }
function HistoryIcon(props) { return <NavIcon {...props}><path d="M3 10a9 9 0 1 1 2 8M3 4v6h6m3-3v5l3 2"/></NavIcon>; }
function DeadLetterIcon(props) { return <NavIcon {...props}><path d="M4 4h16v16H4zM4 14h5l2 3h2l2-3h5m-8-7v3m0 2h.01"/></NavIcon>; }
function PanelToggleIcon(props) { return <NavIcon {...props}><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M9 3v18m7-12-3 3 3 3"/></NavIcon>; }

export default function DashboardSidebar({
  isCollapsed,
  onToggleCollapse,
  mobileOpen,
  onMobileClose,
}) {
  const pathname = usePathname();
  const { user } = useAuth();
  const countKey = user ? JSON.stringify([user.id || user.email, user.workspace_id || user.workspace?.id || null]) : null;
  const counts = useSyncExternalStore(subscribeCounts, () => countCache.get(countKey)?.counts || emptyCounts, () => emptyCounts);
  useEffect(() => {
    if (!countKey) return;
    function refreshCounts() {
      if (document.visibilityState !== "hidden") loadCounts(countKey);
    }
    if (!countCache.has(countKey) || Date.now() - countCache.get(countKey).updated >= 30000) refreshCounts();
    const interval = window.setInterval(refreshCounts, 30000);
    const events = ["focus", "relay:approvals-updated", "relay:dead-letter-updated"];
    events.forEach(event => window.addEventListener(event, refreshCounts));
    document.addEventListener("visibilitychange", refreshCounts);
    return () => {
      window.clearInterval(interval);
      events.forEach(event => window.removeEventListener(event, refreshCounts));
      document.removeEventListener("visibilitychange", refreshCounts);
    };
  }, [countKey]);

  const userName = user?.name || user?.email?.split("@")[0] || "Shaad";
  const userInitial = userName.charAt(0).toUpperCase();

  const mainNavItems = [
    { label: "Dashboard", href: "/dashboard", icon: DashboardIcon },
    { label: "Workflows", href: "/workflows", icon: WorkflowsIcon },
    { label: "Executions", href: "/dashboard/executions", icon: ExecutionsIcon },
    { label: "Approvals", href: "/approvals", icon: ApprovalsIcon },
  ];

  const resourceNavItems = [
    { label: "Connections", href: "/connections", icon: ConnectionsIcon },
    { label: "Knowledge Bases", href: "/dashboard/knowledge-bases", icon: KnowledgeBasesIcon },
  ];

  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  const sidebarContent = (
    <div className="flex flex-col h-full relay-sidebar bg-[var(--surface)] border-r border-[var(--border-subtle)] transition-all duration-150 ease-out select-none overflow-visible">
      {/* Brand Header */}
      <div className={`h-14 flex items-center ${isCollapsed ? "justify-center px-2" : "justify-between px-4"} border-b border-[var(--border-subtle)] shrink-0`}>
        {!isCollapsed ? (
          <>
            <Link href="/dashboard" className="flex items-center gap-3 overflow-hidden">
              {/* Dark Logo (shown in light mode) */}
              <Image
                src="/brand/relay/relay-dark.png"
                alt="Relay Logo"
                width={160}
                height={48}
                priority
                className="w-auto h-9 object-contain dark:hidden block"
              />
              {/* Light Logo (shown in dark mode) */}
              <Image
                src="/brand/relay/relay-light.png"
                alt="Relay Logo"
                width={160}
                height={48}
                priority
                className="w-auto h-9 object-contain hidden dark:block"
              />
            </Link>

            {/* Desktop Sidebar Collapse Toggle */}
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label="Collapse sidebar"
              className="hidden md:flex p-1.5 rounded-[6px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--text-secondary)]/40 cursor-pointer"
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
            className="w-8 h-8 rounded-[6px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--text-secondary)]/40 cursor-pointer"
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
            <div className="px-3 mb-2 text-[10px] font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
              Main
            </div>
          )}
          <nav aria-label="Main Navigation" className="space-y-1">
            {mainNavItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <div key={item.href}>
                <SidebarNavItem
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={isActive && (item.label !== "Executions" || isCollapsed)}
                  collapsed={isCollapsed}
                  badgeCount={item.href === "/approvals" ? counts.approvals : item.label === "Executions" && isCollapsed ? counts.dlq : undefined}
                  badgeLabel={item.label === "Approvals" ? "pending approvals" : "failures needing attention"}
                  onClick={onMobileClose}
                />
                {item.label === "Executions" && !isCollapsed && (
                  <div className="ml-5 mt-1 space-y-0.5 border-l border-[var(--border-subtle)] pl-2">
                    {[
                      { href: "/dashboard/executions", label: "Execution History", icon: HistoryIcon, count: counts.executions },
                      { href: "/dashboard/executions/dead-letter", label: "Dead-Letter Queue", icon: DeadLetterIcon, count: counts.dlq },
                    ].map(({ href, label, icon: Icon, count }) => {
                      const selected = href.endsWith("dead-letter") ? pathname.startsWith(href) : isActive && !pathname.startsWith("/dashboard/executions/dead-letter");
                      return <SidebarNavItem key={href} href={href} label={label} icon={Icon} active={selected} badgeCount={count} badgeLabel={label === "Execution History" ? "workflow runs" : "failures needing attention"} onClick={onMobileClose}/>;
                    })}
                  </div>
                )}
                </div>
              );
            })}
          </nav>
        </div>

        {/* Resources Group */}
        <div>
          {!isCollapsed && (
            <div className="px-3 mb-2 text-[10px] font-medium tracking-wider text-[var(--text-tertiary)] uppercase">
              Resources
            </div>
          )}
          <nav aria-label="Resource Navigation" className="space-y-1">
            {resourceNavItems.map((item) => {
              const isActive = pathname === item.href || (item.href === "/connections" && pathname.startsWith("/connections/")) || (item.href === "/dashboard/knowledge-bases" && pathname.startsWith("/dashboard/knowledge-bases/"));
              const isConnections = item.label === "Connections";
              return (
                <div key={item.href}>
                  <SidebarNavItem href={item.href} label={item.label} icon={item.icon} active={isActive} collapsed={isCollapsed} onClick={onMobileClose} />
                  {isConnections && isActive && !isCollapsed && (
                    <div className="ml-5 mt-1 space-y-0.5 border-l border-[var(--border-subtle)] pl-2">
                      <Link href="/connections" onClick={onMobileClose} aria-current={pathname === "/connections" ? "page" : undefined} className={`group flex h-7 items-center gap-2 rounded-md px-2 text-[12px] transition-colors ${pathname === "/connections" ? "font-medium text-[var(--text-primary)]" : "text-[var(--text-tertiary)] hover:bg-[var(--elevated)]/70 hover:text-[var(--text-primary)]"}`}><span aria-hidden="true" className={`h-1 w-1 rounded-full ${pathname === "/connections" ? "bg-[var(--text-primary)]" : "bg-transparent"}`}/>Connections</Link>
                      <Link href="/connections/webhooks" onClick={onMobileClose} aria-current={pathname === "/connections/webhooks" ? "page" : undefined} className={`group flex h-7 items-center gap-2 rounded-md px-2 text-[12px] transition-colors ${pathname === "/connections/webhooks" ? "font-medium text-[var(--text-primary)]" : "text-[var(--text-tertiary)] hover:bg-[var(--elevated)]/70 hover:text-[var(--text-primary)]"}`}><span aria-hidden="true" className={`h-1 w-1 rounded-full ${pathname === "/connections/webhooks" ? "bg-[var(--text-primary)]" : "bg-transparent"}`}/>Webhooks</Link>
                    </div>
                  )}
                </div>
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
          } rounded-[6px] hover:bg-[var(--elevated)] transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--text-secondary)]/40`}
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
