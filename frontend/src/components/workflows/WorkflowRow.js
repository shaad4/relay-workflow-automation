"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import WorkflowStatus from "./WorkflowStatus";

function MoreHorizontalIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
      <circle cx="5" cy="12" r="1" />
    </svg>
  );
}

function ExternalLinkIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function EditIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function TrashIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

export function formatRelativeTime(dateString) {
  if (!dateString) return "—";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;

  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);

  if (diffInSeconds < 60) {
    return "Just now";
  }
  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  }
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours}h ago`;
  }
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays === 1) {
    return "Yesterday";
  }
  if (diffInDays < 7) {
    return `${diffInDays} days ago`;
  }

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export function formatDate(dateString) {
  if (!dateString) return "—";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function WorkflowRow({ workflow, isLast = false, onDeleteRequest }) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [openUpward, setOpenUpward] = useState(false);
  const menuRef = useRef(null);

  const workflowId = workflow.id;
  const name = workflow.name || "Untitled Workflow";
  const description = workflow.description || "";
  const status = workflow.status || "draft";
  const updatedAt = formatRelativeTime(workflow.updated_at || workflow.created_at);
  const createdAt = formatDate(workflow.created_at);

  const handleCloseMenu = useCallback(() => {
    setMenuOpen(false);
  }, []);

  const handleToggleMenu = (e) => {
    e.stopPropagation();
    if (!menuOpen && menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      setOpenUpward(spaceBelow < 160);
    }
    setMenuOpen((prev) => !prev);
  };

  useEffect(() => {
    if (!menuOpen) return;

    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        handleCloseMenu();
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        handleCloseMenu();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen, handleCloseMenu]);

  const handleRowClick = (e) => {
    if (menuRef.current && menuRef.current.contains(e.target)) {
      return;
    }
    router.push(`/workflows/${workflowId}`);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      if (menuRef.current && menuRef.current.contains(e.target)) {
        return;
      }
      e.preventDefault();
      router.push(`/workflows/${workflowId}`);
    }
  };

  const isDraft = String(status).toLowerCase() === "draft";

  return (
    <div
      role="row"
      tabIndex={0}
      onClick={handleRowClick}
      onKeyDown={handleKeyDown}
      className={`group relative flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 hover:bg-[var(--elevated)]/80 border-b border-[var(--border-subtle)] last:border-b-0 transition-colors duration-100 ease-out cursor-pointer focus:outline-none focus:bg-[var(--elevated)] ${
        isLast ? "rounded-b-lg" : ""
      }`}
    >
      {/* Workflow Name & Description */}
      <div className="min-w-0 flex-1 pr-3">
        <div className="flex items-center gap-2">
          <span className="text-[14px] font-medium text-[var(--text-primary)] group-hover:text-[var(--accent)] transition-colors truncate">
            {name}
          </span>
        </div>
        {description && (
          <p className="text-[12px] text-[var(--text-tertiary)] truncate mt-0.5 max-w-lg font-normal">
            {description}
          </p>
        )}
      </div>

      {/* Columns: Status, Updated, Created, Actions */}
      <div className="flex items-center justify-between sm:justify-end gap-5 sm:gap-6 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-[var(--border-subtle)]/40">
        {/* Status */}
        <div className="w-24 shrink-0">
          <WorkflowStatus status={status} />
        </div>

        {/* Updated At (Monospace Vercel style) */}
        <div className="w-24 shrink-0 text-left font-mono text-[12px] text-[var(--text-tertiary)] hidden md:block">
          {updatedAt}
        </div>

        {/* Created At (Monospace Vercel style) */}
        <div className="w-28 shrink-0 text-left font-mono text-[12px] text-[var(--text-tertiary)] hidden lg:block">
          {createdAt}
        </div>

        {/* Actions Button */}
        <div ref={menuRef} className="w-16 shrink-0 flex justify-end relative">
          <button
            type="button"
            aria-label={`Actions for ${name}`}
            aria-expanded={menuOpen}
            aria-haspopup="true"
            onClick={handleToggleMenu}
            className="p-1 rounded-[4px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface)] transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--accent)] cursor-pointer"
          >
            <MoreHorizontalIcon className="w-4 h-4 stroke-[1.5]" />
          </button>

          {/* Action Popover Menu */}
          {menuOpen && (
            <div
              role="menu"
              className={`absolute right-0 ${
                openUpward ? "bottom-full mb-1" : "top-full mt-1"
              } w-36 bg-[var(--surface)] border border-[var(--border-subtle)] rounded-md shadow-lg p-1 z-50 text-[var(--text-primary)] animate-in fade-in zoom-in-95 duration-100 ease-out select-none`}
            >
              <button
                type="button"
                role="menuitem"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCloseMenu();
                  router.push(`/workflows/${workflowId}`);
                }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 text-[12px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] rounded-[4px] transition-colors cursor-pointer text-left"
              >
                <ExternalLinkIcon className="w-3.5 h-3.5 stroke-[1.5]" />
                <span>Open</span>
              </button>

              <button
                type="button"
                role="menuitem"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCloseMenu();
                  router.push(`/workflows/${workflowId}`);
                }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 text-[12px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] rounded-[4px] transition-colors cursor-pointer text-left"
              >
                <EditIcon className="w-3.5 h-3.5 stroke-[1.5]" />
                <span>Edit</span>
              </button>

              <div className="my-1 border-t border-[var(--border-subtle)]" />

              {isDraft ? (
                <button
                  type="button"
                  role="menuitem"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCloseMenu();
                    if (onDeleteRequest) {
                      onDeleteRequest(workflow);
                    }
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 text-[12px] font-medium text-red-500 dark:text-red-400 hover:bg-red-500/10 rounded-[4px] transition-colors cursor-pointer text-left"
                >
                  <TrashIcon className="w-3.5 h-3.5 stroke-[1.5]" />
                  <span>Delete</span>
                </button>
              ) : (
                <button
                  type="button"
                  role="menuitem"
                  disabled
                  title="Only draft workflows can be deleted"
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                  className="w-full flex items-center justify-between px-2.5 py-1.5 text-[12px] font-medium text-[var(--text-disabled)] opacity-40 cursor-not-allowed select-none rounded-[4px]"
                >
                  <div className="flex items-center gap-2">
                    <TrashIcon className="w-3.5 h-3.5 stroke-[1.5]" />
                    <span>Delete</span>
                  </div>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
