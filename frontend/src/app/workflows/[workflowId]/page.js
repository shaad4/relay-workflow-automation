"use client";

import { use } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import DashboardShell from "@/components/dashboard/DashboardShell";

function ArrowLeftIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  );
}

function WorkflowIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="18" r="3" />
      <path d="M18 6a3 3 0 0 0-3 3v6a3 3 0 0 1-3 3H9" />
    </svg>
  );
}

export default function WorkflowDetailPage({ params }) {
  const resolvedParams = use(params);
  const workflowId = resolvedParams?.workflowId || "";

  return (
    <ProtectedRoute>
      <DashboardShell pageTitle="Workflow Editor">
        <div className="w-full max-w-7xl mx-auto space-y-6">
          <div className="flex items-center gap-3 pb-2 border-b border-[var(--border-subtle)]">
            <Link
              href="/workflows"
              className="p-1.5 rounded-[6px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface)] transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            >
              <ArrowLeftIcon className="w-4 h-4 stroke-[1.5]" />
            </Link>
            <div>
              <h1 className="text-[24px] leading-[30px] font-semibold text-[var(--text-primary)] tracking-tight">
                Workflow Details
              </h1>
              <p className="mt-0.5 text-[14px] leading-[22px] text-[var(--text-secondary)] font-mono">
                ID: {workflowId}
              </p>
            </div>
          </div>

          <div className="w-full bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl p-8 sm:p-12 text-center my-4 select-none">
            <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-4 text-[var(--accent)]">
              <WorkflowIcon className="w-6 h-6 stroke-[1.5]" />
            </div>

            <h3 className="text-[16px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
              Workflow Editor Placeholder
            </h3>

            <p className="text-[14px] text-[var(--text-secondary)] max-w-md mx-auto mb-6 leading-relaxed">
              The Workflow Editor for workflow &quot;<span className="font-mono text-[var(--text-primary)]">{workflowId}</span>&quot; will be implemented in the next step.
            </p>

            <Link
              href="/workflows"
              className="inline-flex items-center gap-2 h-9 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[14px] font-medium text-[var(--text-primary)] transition-all duration-100 ease-out focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 cursor-pointer"
            >
              <ArrowLeftIcon className="w-4 h-4 stroke-[1.5]" />
              <span>Back to Workflows</span>
            </Link>
          </div>
        </div>
      </DashboardShell>
    </ProtectedRoute>
  );
}
