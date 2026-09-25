"use client";

import { useState } from "react";
import DashboardSidebar from "./DashboardSidebar";
import DashboardNavbar from "./DashboardNavbar";

export default function DashboardShell({ children, pageTitle = "Dashboard" }) {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("relay-sidebar-collapsed");
        if (saved !== null) {
          return saved === "true";
        }
      } catch {
        // Fallback if localStorage is unavailable
      }
    }
    return false;
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleToggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("relay-sidebar-collapsed", String(next));
      } catch {
        // Ignore localStorage write errors
      }
      return next;
    });
  };

  return (
    <div className="flex min-h-screen bg-[var(--canvas)] text-[var(--text-primary)] font-sans antialiased">
      {/* Sidebar (Desktop + Mobile Drawer) */}
      <DashboardSidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={handleToggleCollapse}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 transition-all duration-150 ease-out">
        {/* Top Navbar */}
        <DashboardNavbar
          onMobileMenuToggle={() => setMobileOpen(true)}
          pageTitle={pageTitle}
        />

        {/* Page Content */}
        <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
