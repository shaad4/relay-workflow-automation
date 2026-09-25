"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";

// Line SVG Icons (1.5px stroke)
function SunIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </svg>
  );
}

function MoonIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  );
}

function MonitorIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <rect width="20" height="14" x="2" y="3" rx="2" />
      <line x1="8" x2="16" y1="21" y2="21" />
      <line x1="12" x2="12" y1="17" y2="21" />
    </svg>
  );
}

function ChevronRightIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}

function ChevronLeftIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}

function LogOutIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" x2="9" y1="12" y2="12" />
    </svg>
  );
}

function CheckIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export default function ProfileMenu({ open, onClose, positionClass = "bottom-full mb-2 left-0" }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const [view, setView] = useState("main"); // "main" | "appearance"
  const menuRef = useRef(null);

  const userName = user?.name || (user?.email ? user.email.split("@")[0] : "User");
  const userEmail = user?.email || "";

  const handleClose = useCallback(() => {
    setView("main");
    onClose();
  }, [onClose]);

  // Handle outside click & Escape key
  useEffect(() => {
    if (!open) return;

    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        handleClose();
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        handleClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, handleClose]);

  if (!open) return null;

  const handleLogout = () => {
    handleClose();
    logout();
    router.replace("/login");
  };

  const currentThemeIcon =
    theme === "light" ? (
      <SunIcon className="w-4 h-4 stroke-[1.5]" />
    ) : theme === "dark" ? (
      <MoonIcon className="w-4 h-4 stroke-[1.5]" />
    ) : (
      <MonitorIcon className="w-4 h-4 stroke-[1.5]" />
    );

  const currentThemeLabel =
    theme === "light" ? "Light" : theme === "dark" ? "Dark" : "System";

  return (
    <div
      ref={menuRef}
      role="menu"
      aria-orientation="vertical"
      className={`absolute ${positionClass} w-64 bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl shadow-lg p-1.5 z-50 text-[var(--text-primary)] animate-in fade-in zoom-in-95 duration-100 ease-out select-none`}
    >
      {view === "main" ? (
        <div>
          {/* User Information Header */}
          <div className="px-3 py-2.5 mb-1 border-b border-[var(--border-subtle)]">
            <p className="text-[13px] font-semibold text-[var(--text-primary)] truncate leading-tight">
              {userName}
            </p>
            {userEmail && (
              <p className="text-[12px] text-[var(--text-tertiary)] truncate mt-0.5">
                {userEmail}
              </p>
            )}
          </div>

          {/* Appearance Option */}
          <button
            type="button"
            role="menuitem"
            onClick={() => setView("appearance")}
            className="w-full flex items-center justify-between px-3 py-2 text-[13px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] rounded-[6px] transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--accent)]/40"
          >
            <div className="flex items-center gap-2.5">
              <span className="text-[var(--text-tertiary)]">{currentThemeIcon}</span>
              <span>Appearance</span>
            </div>
            <div className="flex items-center gap-1.5 text-[var(--text-tertiary)]">
              <span className="text-[12px] capitalize">{currentThemeLabel}</span>
              <ChevronRightIcon className="w-4 h-4 stroke-[1.5]" />
            </div>
          </button>

          {/* Divider */}
          <div className="my-1 border-t border-[var(--border-subtle)]" />

          {/* Logout Option */}
          <button
            type="button"
            role="menuitem"
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-[13px] font-medium text-[var(--text-secondary)] hover:text-red-500 dark:hover:text-red-400 hover:bg-red-500/10 rounded-[6px] transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-red-400/40"
          >
            <LogOutIcon className="w-4 h-4 stroke-[1.5]" />
            <span>Log out</span>
          </button>
        </div>
      ) : (
        /* Appearance Submenu */
        <div>
          {/* Submenu Header */}
          <button
            type="button"
            onClick={() => setView("main")}
            className="w-full flex items-center gap-2 px-2 py-2 mb-1 text-[13px] font-semibold text-[var(--text-primary)] hover:bg-[var(--elevated)] rounded-[6px] transition-colors cursor-pointer border-b border-[var(--border-subtle)] focus:outline-none"
          >
            <ChevronLeftIcon className="w-4 h-4 stroke-[1.5] text-[var(--text-tertiary)]" />
            <span>Appearance</span>
          </button>

          {/* Theme Options */}
          <div className="space-y-0.5 pt-1">
            {[
              { id: "system", label: "System", icon: MonitorIcon },
              { id: "light", label: "Light", icon: SunIcon },
              { id: "dark", label: "Dark", icon: MoonIcon },
            ].map((option) => {
              const isSelected = theme === option.id;
              const Icon = option.icon;
              return (
                <button
                  key={option.id}
                  type="button"
                  role="menuitemradio"
                  aria-checked={isSelected}
                  onClick={() => setTheme(option.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 text-[13px] font-medium rounded-[6px] transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-[var(--accent)]/40 ${
                    isSelected
                      ? "bg-[var(--elevated)] text-[var(--text-primary)]"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)]"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4 stroke-[1.5] text-[var(--text-tertiary)]" />
                    <span>{option.label}</span>
                  </div>
                  {isSelected && (
                    <CheckIcon className="w-4 h-4 stroke-[2] text-[var(--text-primary)]" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
