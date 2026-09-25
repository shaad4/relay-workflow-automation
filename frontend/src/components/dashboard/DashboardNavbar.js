"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import ProfileMenu from "./ProfileMenu";

function MenuIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="4" x2="20" y1="12" y2="12" />
      <line x1="4" x2="20" y1="6" y2="6" />
      <line x1="4" x2="20" y1="18" y2="18" />
    </svg>
  );
}

function SearchIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function HelpIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" x2="12.01" y1="17" y2="17" />
    </svg>
  );
}

function BellIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}

export default function DashboardNavbar({
  onMobileMenuToggle,
  pageTitle = "Dashboard",
}) {
  const { user } = useAuth();
  const userName = user?.name || user?.email?.split("@")[0] || "Shaad";
  const userInitial = userName.charAt(0).toUpperCase();

  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 h-[56px] w-full bg-[var(--canvas)] border-b border-[var(--border-subtle)] px-4 sm:px-6 flex items-center justify-between select-none">
      {/* Left Section: Mobile Hamburger & Page Title */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMobileMenuToggle}
          aria-label="Open navigation menu"
          className="md:hidden p-1.5 rounded-[6px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] border border-[var(--border-subtle)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 cursor-pointer"
        >
          <MenuIcon className="w-4 h-4 stroke-[1.5]" />
        </button>

        <h1 className="text-[14px] font-semibold text-[var(--text-primary)] tracking-tight">
          {pageTitle}
        </h1>
      </div>

      {/* Right Section: Search, Help, Notifications, User Avatar */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Search Placeholder Button */}
        <button
          type="button"
          aria-label="Search"
          className="h-8 px-2.5 rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface)] hover:bg-[var(--elevated)] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] text-[12px] flex items-center gap-2 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
        >
          <SearchIcon className="w-3.5 h-3.5 stroke-[1.5]" />
          <span className="hidden sm:inline">Search...</span>
          <kbd className="hidden sm:inline px-1.5 py-0.5 text-[10px] font-mono bg-[var(--elevated)] border border-[var(--border-subtle)] rounded text-[var(--text-tertiary)]">
            ⌘K
          </kbd>
        </button>

        {/* Help Placeholder Button */}
        <button
          type="button"
          aria-label="Help and Documentation"
          className="w-8 h-8 rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface)] hover:bg-[var(--elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center justify-center transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
        >
          <HelpIcon className="w-4 h-4 stroke-[1.5]" />
        </button>

        {/* Notifications Placeholder Button */}
        <button
          type="button"
          aria-label="Notifications"
          className="w-8 h-8 rounded-[6px] border border-[var(--border-subtle)] bg-[var(--surface)] hover:bg-[var(--elevated)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center justify-center transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 relative"
        >
          <BellIcon className="w-4 h-4 stroke-[1.5]" />
        </button>

        {/* User Avatar Button with Profile Menu Popover */}
        <div className="relative ml-1">
          <button
            type="button"
            aria-label="User profile menu"
            aria-expanded={profileMenuOpen}
            aria-haspopup="true"
            onClick={() => setProfileMenuOpen((prev) => !prev)}
            className="w-8 h-8 rounded-[6px] bg-[var(--elevated)] border border-[var(--border-default)] hover:border-[var(--border-strong)] flex items-center justify-center font-bold text-[13px] text-[var(--text-primary)] transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40"
          >
            {userInitial}
          </button>

          <ProfileMenu
            open={profileMenuOpen}
            onClose={() => setProfileMenuOpen(false)}
            positionClass="top-full mt-2 right-0 w-64"
          />
        </div>
      </div>
    </header>
  );
}
