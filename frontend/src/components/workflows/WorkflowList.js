"use client";

import { useState } from "react";
import WorkflowRow from "./WorkflowRow";
import { useAuth } from "@/context/AuthContext";
import { deleteWorkflow } from "@/services/workflows";

function AlertTriangleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

export default function WorkflowList({ workflows = [], onDeleteSuccess }) {
  const { accessToken } = useAuth();
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;

    try {
      setIsDeleting(true);
      await deleteWorkflow(accessToken, deleteTarget.id);
      const deletedId = deleteTarget.id;
      setDeleteTarget(null);
      if (onDeleteSuccess) {
        onDeleteSuccess(deletedId);
      }
    } catch (err) {
      console.error("Failed to delete workflow:", err);
      if (onDeleteSuccess) {
        onDeleteSuccess(deleteTarget.id);
      }
      setDeleteTarget(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="w-full">
      {/* Vercel-Style Table Container (overflow-visible to prevent popover clipping) */}
      <div className="w-full bg-[var(--surface)] border border-[var(--border-subtle)] rounded-lg font-sans">
        {/* Table Monospace Header */}
        <div className="hidden sm:flex items-center justify-between gap-4 h-9 px-4 border-b border-[var(--border-subtle)] bg-[var(--elevated)]/60 rounded-t-lg text-[11px] font-mono tracking-wider uppercase text-[var(--text-tertiary)] select-none">
          <div className="flex-1">Workflow</div>
          <div className="flex items-center justify-end gap-5 sm:gap-6 shrink-0">
            <div className="w-24">Status</div>
            <div className="w-24 hidden md:block text-left">Updated</div>
            <div className="w-28 hidden lg:block text-left">Created</div>
            <div className="w-16 text-right">Actions</div>
          </div>
        </div>

        {/* Workflow Rows */}
        <div className="divide-y divide-[var(--border-subtle)]">
          {workflows.map((wf, index) => (
            <WorkflowRow
              key={wf.id}
              workflow={wf}
              isLast={index === workflows.length - 1}
              onDeleteRequest={(target) => {
                const isDraft = String(target?.status || "").toLowerCase() === "draft";
                if (isDraft) {
                  setDeleteTarget(target);
                }
              }}
            />
          ))}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-100 font-sans">
          <div className="w-full max-w-md bg-[var(--surface)] border border-[var(--border-subtle)] rounded-lg p-6 shadow-xl text-left select-none">
            <div className="flex items-start gap-3.5 mb-4">
              <div className="w-9 h-9 rounded-[6px] bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 shrink-0">
                <AlertTriangleIcon className="w-4 h-4 stroke-[1.5]" />
              </div>
              <div>
                <h3 className="text-[15px] font-semibold text-[var(--text-primary)] leading-snug">
                  Delete Workflow?
                </h3>
                <p className="text-[13px] text-[var(--text-secondary)] mt-1 leading-relaxed">
                  Are you sure you want to delete &quot;<span className="font-medium text-[var(--text-primary)]">{deleteTarget.name}</span>&quot;? This action cannot be undone.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border-subtle)]">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setDeleteTarget(null)}
                className="h-8 px-3 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] text-[12px] font-medium text-[var(--text-primary)] transition-colors cursor-pointer disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={handleDeleteConfirm}
                className="h-8 px-3 rounded-[6px] bg-red-600 hover:bg-red-700 text-white text-[12px] font-medium transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
              >
                {isDeleting ? (
                  <>
                    <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <span>Delete</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
