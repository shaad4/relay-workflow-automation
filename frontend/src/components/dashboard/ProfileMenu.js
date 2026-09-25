"use client";

import { useEffect, useRef, useCallback } from "react";
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

function LogOutIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" x2="9" y1="12" y2="12" />
    </svg>
  );
}

export default function ProfileMenu({ open, onClose, positionClass = "bottom-full mb-2 left-0" }) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const menuRef = useRef(null);

  const userName = user?.name || (user?.email ? user.email.split("@")[0] : "User");
  const userEmail = user?.email || "";

  const handleClose = useCallback(() => {
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

  return (
    <div
      ref={menuRef}
      role="menu"
      aria-orientation="vertical"
      className={`absolute ${positionClass} w-64 bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl shadow-lg p-1.5 z-50 text-[var(--text-primary)] animate-in fade-in zoom-in-95 duration-100 ease-out select-none`}
    >
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

      {/* Direct Theme Switcher Toggle Row */}
      <div className="px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-[13px] font-medium text-[var(--text-secondary)]">
          <span className="text-[var(--text-tertiary)]">{currentThemeIcon}</span>
          <span>Theme</span>
        </div>

        {/* 3-Segment Toggle Switch */}
        <div className="flex items-center p-0.5 bg-[var(--elevated)] border border-[var(--border-subtle)] rounded-[6px]">
          {[
            { id: "light", label: "Light", icon: SunIcon },
            { id: "dark", label: "Dark", icon: MoonIcon },
            { id: "system", label: "System", icon: MonitorIcon },
          ].map((opt) => {
            const isSelected = theme === opt.id;
            const Icon = opt.icon;
            return (
              <button
                key={opt.id}
                type="button"
                title={`Switch to ${opt.label} mode`}
                aria-label={`${opt.label} theme`}
                onClick={() => setTheme(opt.id)}
                className={`p-1.5 rounded-[4px] transition-all duration-100 cursor-pointer focus:outline-none ${
                  isSelected
                    ? "bg-[var(--surface)] text-[var(--text-primary)] border border-[var(--border-subtle)] shadow-2xs"
                    : "text-[var(--text-tertiary)] hover:text-[var(--text-primary)] border border-transparent"
                }`}
              >
                <Icon className="w-3.5 h-3.5 stroke-[1.5]" />
              </button>
            );
          })}
        </div>
      </div>

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
  );
}
