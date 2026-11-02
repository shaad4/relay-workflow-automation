"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import DashboardShell from "@/components/dashboard/DashboardShell";

const desktopQuery = "(min-width: 1024px)";
const getScreenSnapshot = () => window.matchMedia(desktopQuery).matches;
const getServerSnapshot = () => null;
function subscribeToScreen(callback) {
  const query = window.matchMedia(desktopQuery);
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
}

export default function WorkflowScreenGate({ workflowId, children }) {
  const isDesktop = useSyncExternalStore(
    subscribeToScreen,
    getScreenSnapshot,
    getServerSnapshot,
  );
  // Keep an opened editor mounted when resizing so unsaved edits survive.
  // A mobile visit never mounts the editor or starts its data requests.
  const [desktopOpened, setDesktopOpened] = useState(false);
  if (isDesktop && !desktopOpened) setDesktopOpened(true);

  return (
    <>
      {desktopOpened && (
        <div className={isDesktop ? "block" : "hidden"}>{children}</div>
      )}
      {!isDesktop && (
        <DashboardShell pageTitle="Workflow Builder">
          {isDesktop === null ? (
            <p
              role="status"
              className="py-12 text-center text-sm text-[var(--text-secondary)]"
            >
              Loading workflow…
            </p>
          ) : (
            <LargerScreenMessage key={workflowId} workflowId={workflowId} />
          )}
        </DashboardShell>
      )}
    </>
  );
}

function LargerScreenMessage({ workflowId }) {
  const [status, setStatus] = useState("");
  const [manualLink, setManualLink] = useState("");
  const [sharing, setSharing] = useState(false);
  const workflowUrl = () =>
    new URL(
      `/workflows/${encodeURIComponent(workflowId)}`,
      window.location.origin,
    ).href;

  async function copyLink() {
    const url = workflowUrl();
    try {
      await navigator.clipboard.writeText(url);
      setManualLink("");
      setStatus("Link copied. Open it on your laptop or desktop.");
    } catch {
      setManualLink(url);
      setStatus("Select and copy the link below.");
    }
  }

  async function shareLink() {
    setStatus("");
    if (!navigator.share) {
      await copyLink();
      return;
    }
    setSharing(true);
    try {
      await navigator.share({
        title: "Open workflow in Relay",
        text: "Open this workflow on a laptop or desktop to build in Relay.",
        url: workflowUrl(),
      });
    } catch (error) {
      if (error?.name !== "AbortError") await copyLink();
    } finally {
      setSharing(false);
    }
  }

  const buttonClass =
    "inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md px-4 text-[13px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--text-primary)] disabled:opacity-50";

  return (
    <section className="mx-auto flex min-h-[65svh] w-full max-w-sm flex-col justify-center py-8 text-center">
      <svg
        className="mx-auto mb-6 h-14 w-14 text-[var(--text-secondary)]"
        viewBox="0 0 48 48"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <rect x="8" y="8" width="32" height="24" rx="3" />
        <path d="M8 32 3 38c0 1 1 2 3 2h36c2 0 3-1 3-2l-5-6M19 36h10" />
        <path d="m19 17-4 4 4 4m10-8 4 4-4 4" />
      </svg>
      <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">
        Build on a bigger screen
      </h1>
      <p className="mt-3 text-[13px] leading-6 text-[var(--text-secondary)]">
        Open this workflow on a laptop or desktop to build and edit it. Send
        yourself the link to continue there.
      </p>
      <div className="mt-7 grid gap-3">
        <button
          type="button"
          onClick={shareLink}
          disabled={sharing}
          className={`${buttonClass} bg-[var(--accent)] text-[var(--accent-foreground)] hover:bg-[var(--accent-hover)]`}
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 16V3m-4 4 4-4 4 4M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7" />
          </svg>
          {sharing ? "Sharing…" : "Share workflow link"}
        </button>
        <button
          type="button"
          onClick={copyLink}
          className={`${buttonClass} border border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--elevated)]`}
        >
          Copy link
        </button>
      </div>
      <p
        role="status"
        className="mt-3 text-xs leading-5 text-[var(--text-secondary)]"
      >
        {status}
      </p>
      {manualLink && (
        <label className="mt-2 text-left text-xs text-[var(--text-secondary)]">
          Workflow link
          <input
            readOnly
            value={manualLink}
            onFocus={(event) => event.target.select()}
            className="mt-2 min-h-11 w-full rounded-md border border-[var(--border-default)] bg-[var(--input-bg)] px-3 text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--text-primary)]"
          />
        </label>
      )}
      <p className="mt-4 text-xs leading-5 text-[var(--text-tertiary)]">
        Sign in to the same Relay workspace on your computer. Sharing a link
        doesn’t grant access to the workflow.
      </p>
      <Link
        href="/workflows"
        className="mx-auto mt-6 inline-flex min-h-11 items-center rounded px-3 text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-[var(--text-primary)]"
      >
        ← Back to workflows
      </Link>
    </section>
  );
}
