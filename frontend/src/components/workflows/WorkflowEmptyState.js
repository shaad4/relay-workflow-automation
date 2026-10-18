"use client";

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

export default function WorkflowEmptyState({ onCreateNew }) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface)] px-6 py-12 text-center sm:px-12 sm:py-16">
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-[radial-gradient(ellipse_at_50%_0,var(--accent),transparent_70%)] opacity-[.10]" />
      <div className="relative mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl border border-[var(--accent)]/20 bg-[var(--accent)]/10 text-[var(--accent)]">
        <WorkflowIcon aria-hidden="true" className="h-6 w-6 stroke-[1.5]" />
      </div>
      <p className="relative mb-2 font-mono text-[10px] uppercase tracking-[.17em] text-[var(--accent)]">Make your work flow</p>
      <h2 className="relative text-[18px] font-semibold tracking-tight text-[var(--text-primary)] sm:text-[20px]">No workflows yet</h2>
      <p className="relative mx-auto mt-2 max-w-md text-[13px] leading-6 text-[var(--text-secondary)]">Turn a repeatable task into a workflow. Connect your tools, add logic or approvals, and let each step lead to the next.</p>
      <button type="button" onClick={onCreateNew} disabled={!onCreateNew} className="relative mt-6 inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 text-[13px] font-medium text-white transition-colors hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)] disabled:cursor-not-allowed disabled:opacity-50">
        <PlusIcon aria-hidden="true" className="h-4 w-4 stroke-[1.8]" />Create your first workflow
      </button>
      <ol className="relative mx-auto mt-10 grid max-w-xl grid-cols-1 gap-4 border-t border-[var(--border-subtle)] pt-5 text-left sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-[var(--border-subtle)]">
        {[
          ["Choose a trigger", "Start manually, on a schedule, or from a webhook."],
          ["Connect your steps", "Add actions, AI, and human approvals."],
          ["Publish your workflow", "Validate your setup and put it to work."],
        ].map(([title, description], index) => (
          <li key={title} className="px-3"><span className="font-mono text-[10px] text-[var(--text-tertiary)]">0{index + 1}</span><p className="mt-1 text-[11px] font-medium text-[var(--text-primary)]">{title}</p><p className="mt-1 text-[11px] leading-4 text-[var(--text-tertiary)]">{description}</p></li>
        ))}
      </ol>
    </section>
  );
}
