"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { activateWorkflow, deactivateWorkflow } from "@/services/workflows";
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

function WorkflowMark({ name = "Workflow" }) {
  const hue = Array.from(name).reduce((value, char) => value + char.charCodeAt(0), 0) % 360;
  return (
    <div className="relative flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--elevated)] text-[var(--text-primary)]">
      <div className="absolute inset-0 opacity-20" style={{ background: `radial-gradient(circle at 30% 20%, hsl(${hue} 85% 65%), transparent 70%)` }} />
      <svg className="relative h-5 w-5" viewBox="0 0 24 24" fill="none" stroke={`hsl(${hue} 75% 62%)`} strokeWidth="1.6" aria-hidden="true">
        <circle cx="5" cy="6" r="2.2" />
        <circle cx="19" cy="18" r="2.2" />
        <circle cx="18" cy="6" r="2.2" />
        <path d="M7.2 6H12a4 4 0 0 1 4 4v5.8M16 6h-.2" />
        <path d="M16.4 15.8H12a4 4 0 0 1-4-4V8.2" />
      </svg>
    </div>
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

export default function WorkflowRow({ workflow, onDeleteRequest, onWorkflowStatusChange }) {
  const router = useRouter();
  const { accessToken } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [openUpward, setOpenUpward] = useState(false);
  const [isChangingStatus, setIsChangingStatus] = useState(false);
  const [showStatusConfirm, setShowStatusConfirm] = useState(false);
  const [statusError, setStatusError] = useState("");
  const menuRef = useRef(null);

  const workflowId = workflow.id;
  const name = workflow.name || "Untitled Workflow";
  const description = workflow.description || "";
  const status = workflow.status || "draft";
  const updatedAt = formatRelativeTime(workflow.updated_at || workflow.created_at);

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

  const normalizedStatus = String(status).toLowerCase();
  const isDraft = normalizedStatus === "draft";
  const canToggleStatus = normalizedStatus === "active" || normalizedStatus === "inactive" || normalizedStatus === "published";
  const isActive = normalizedStatus === "active" || normalizedStatus === "published";

  const handleToggleStatus = async (e) => {
    e.stopPropagation();
    if (isChangingStatus || !canToggleStatus) return;
    setIsChangingStatus(true);
    setStatusError("");
    try {
      const response = isActive
        ? await deactivateWorkflow(accessToken, workflowId)
        : await activateWorkflow(accessToken, workflowId);
      onWorkflowStatusChange?.(workflowId, response?.status || (isActive ? "inactive" : "active"));
      setShowStatusConfirm(false);
    } catch (error) {
      setStatusError(error?.message || `Unable to ${isActive ? "deactivate" : "activate"} workflow.`);
    } finally {
      setIsChangingStatus(false);
    }
  };

  return (
    <div
      role="link"
      tabIndex={0}
      onClick={handleRowClick}
      onKeyDown={handleKeyDown}
      className="group relative flex min-h-[216px] flex-col overflow-visible rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-4 text-left shadow-sm transition-all duration-150 hover:-translate-y-0.5 hover:border-[var(--border-strong)] hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40"
    >
      <div className="flex items-start gap-3 pr-9">
        <WorkflowMark name={name} />
        <div className="min-w-0 flex-1 pt-0.5">
          <div className="truncate text-[15px] font-semibold tracking-tight text-[var(--text-primary)] group-hover:text-[var(--accent)] transition-colors">{name}</div>
          <div className="mt-1 truncate font-mono text-[10px] text-[var(--text-tertiary)]">/workflows/{workflowId.slice(0, 8)}</div>
        </div>
      </div>

      <p className="mt-4 min-h-[54px] text-[13px] leading-[19px] text-[var(--text-secondary)] line-clamp-3">
        {description || <span className="italic text-[var(--text-tertiary)]">No description added yet.</span>}
      </p>

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-[var(--border-subtle)] pt-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <WorkflowStatus status={status} />
          <span className="h-1 w-1 rounded-full bg-[var(--border-strong)]" />
          <span className="truncate text-[11px] text-[var(--text-tertiary)]">Updated {updatedAt}</span>
        </div>
        <span className="shrink-0 text-[11px] font-medium text-[var(--accent)] opacity-0 transition-opacity group-hover:opacity-100">Open ↗</span>
      </div>

      <div ref={menuRef} className="absolute right-3 top-3 z-10">
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

              {canToggleStatus && (
                <button
                  type="button"
                  role="menuitem"
                  disabled={isChangingStatus}
                  onClick={(event) => {
                    event.stopPropagation();
                    setStatusError("");
                    handleCloseMenu();
                    setShowStatusConfirm(true);
                  }}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 text-[12px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] rounded-[4px] transition-colors cursor-pointer text-left disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isChangingStatus ? (isActive ? "Deactivating..." : "Activating...") : isActive ? "Deactivate" : "Activate"}
                </button>
              )}

              {statusError && <p role="alert" className="px-2.5 py-1 text-[11px] leading-4 text-red-500">{statusError}</p>}

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

      {showStatusConfirm && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/55 p-4 backdrop-blur-[2px]" role="presentation" onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()} onMouseDown={(event) => { if (event.target === event.currentTarget && !isChangingStatus) setShowStatusConfirm(false); }}>
          <section role="dialog" aria-modal="true" aria-labelledby={`workflow-status-confirm-${workflowId}`} className="w-full max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] p-5 text-left shadow-2xl">
            <h2 id={`workflow-status-confirm-${workflowId}`} className="text-[16px] font-semibold text-[var(--text-primary)]">
              {isActive ? "Deactivate workflow?" : "Activate workflow?"}
            </h2>
            <p className="mt-2 text-[13px] leading-5 text-[var(--text-secondary)]">
              {isActive
                ? "This will stop the entire workflow from running. The change applies to all versions, not only the version currently selected."
                : "This will enable the entire workflow to run. The change applies to all versions, not only the version currently selected."}
            </p>
            {statusError && <p role="alert" className="mt-3 text-[12px] text-red-500">{statusError}</p>}
            <div className="mt-5 flex justify-end gap-2 border-t border-[var(--border-subtle)] pt-3">
              <button type="button" disabled={isChangingStatus} onClick={() => setShowStatusConfirm(false)} className="h-8 rounded-lg border border-[var(--border-default)] px-3 text-[12px] font-medium text-[var(--text-secondary)] hover:bg-[var(--elevated)] disabled:opacity-50">Cancel</button>
              <button type="button" disabled={isChangingStatus} onClick={handleToggleStatus} className={`inline-flex h-8 items-center gap-2 rounded-lg px-3 text-[12px] font-medium text-white disabled:opacity-50 ${isActive ? "bg-red-600 hover:bg-red-700" : "bg-[var(--accent)] hover:opacity-90"}`}>
                {isChangingStatus && <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />}
                {isChangingStatus ? (isActive ? "Deactivating..." : "Activating...") : (isActive ? "Deactivate workflow" : "Activate workflow")}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
