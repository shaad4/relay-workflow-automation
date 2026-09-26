"use client";

import Link from "next/link";

function PlusIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
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

export default function WorkflowEmptyState() {
  return (
    <div className="w-full bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl p-8 sm:p-12 text-center my-4 select-none">
      <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-4 text-[var(--text-tertiary)]">
        <WorkflowIcon className="w-6 h-6 stroke-[1.5]" />
      </div>

      <h3 className="text-[16px] font-semibold text-[var(--text-primary)] tracking-tight mb-1">
        No workflows yet
      </h3>

      <p className="text-[14px] text-[var(--text-secondary)] max-w-sm mx-auto mb-6 leading-relaxed">
        Create your first workflow to automate a process.
      </p>

      <Link
        href="/workflows/new"
        className="inline-flex items-center gap-2 h-9 px-4 rounded-[6px] bg-[#4F46E5] hover:bg-[#6366F1] active:opacity-90 text-white font-medium text-[14px] transition-all duration-100 ease-out focus:outline-none focus:ring-2 focus:ring-[#4F46E5]/40 cursor-pointer shadow-none"
      >
        <PlusIcon className="w-4 h-4 stroke-[2]" />
        <span>New Workflow</span>
      </Link>
    </div>
  );
}
