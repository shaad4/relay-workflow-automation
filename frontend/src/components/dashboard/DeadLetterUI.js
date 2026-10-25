"use client";

import { useEffect, useRef } from "react";
import { ExecutionIcon, executionAction, executionButton } from "./ExecutionUI";
import { deadLetterError } from "@/lib/deadLetter";

export function DeadLetterError({ error, onRetry, busy }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-500/25 bg-red-500/5 p-5"
    >
      <h2 className="text-sm font-semibold">
        {error?.status === 404
          ? "Event not found"
          : "Unable to complete request"}
      </h2>
      <p className="mt-2 text-xs text-[var(--text-secondary)]">
        {deadLetterError(error)}
      </p>
      <button
        disabled={busy}
        onClick={onRetry}
        className={`${executionButton} mt-3`}
      >
        Retry
      </button>
    </div>
  );
}

export function DeadLetterConfirmation({
  action,
  busy,
  error,
  onClose,
  onConfirm,
  title,
  description,
  cancelLabel = "Cancel",
  confirmLabel,
}) {
  const dialog = useRef(null);
  const cancel = useRef(null);
  const replay = action === "replay";
  useEffect(() => {
    const previous = document.activeElement;
    const element = dialog.current;
    element.showModal();
    cancel.current?.focus();
    return () => {
      element.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      aria-labelledby="dlq-confirm-title"
      aria-describedby="dlq-confirm-description"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-md rounded-xl border border-[var(--border-default)] bg-[var(--surface)] p-6 text-[var(--text-primary)] shadow-2xl backdrop:bg-black/65"
    >
      <span
        className={`dlq-confirm-icon ${replay ? "is-replay" : "is-resolve"}`}
      >
        <ExecutionIcon type={replay ? "replay" : "check"} className="h-5 w-5" />
      </span>
      <h2 id="dlq-confirm-title" className="text-lg font-semibold">
        {title ||
          (replay ? "Replay Failed Execution?" : "Resolve Dead-Letter Event?")}
      </h2>
      <p
        id="dlq-confirm-description"
        className="mt-3 text-sm leading-6 text-[var(--text-secondary)]"
      >
        {description ||
          (replay
            ? "This will create a new execution starting from the failed node. The execution may fail again. Only workflows that pass Relay's replay safety checks can be replayed."
            : "This will mark the failed execution as handled without running it again.")}
      </p>
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-700 dark:text-red-400">
          {deadLetterError(error)}
        </p>
      )}
      <div className="mt-6 flex flex-wrap justify-end gap-2">
        <button
          ref={cancel}
          disabled={busy}
          onClick={onClose}
          className={executionButton}
        >
          {cancelLabel}
        </button>
        <button
          disabled={busy || Boolean(error)}
          onClick={onConfirm}
          className={`${executionAction} ${replay ? "is-primary" : "is-resolve"}`}
        >
          {busy
            ? "Processing…"
            : confirmLabel ||
              (replay ? "Replay Execution" : "Mark as Resolved")}
        </button>
      </div>
    </dialog>
  );
}
