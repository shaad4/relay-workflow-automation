"use client";

import { useEffect, useRef } from "react";

export default function DocumentDeleteDialog({
  document,
  onClose,
  onDelete,
  busy,
  error,
  fallbackFocusRef,
}) {
  const dialog = useRef(null);
  const cancel = useRef(null);
  useEffect(() => {
    const previous = window.document.activeElement;
    const element = dialog.current;
    const fallback = fallbackFocusRef.current;
    element.showModal();
    cancel.current?.focus();
    return () => {
      element.close();
      if (previous?.isConnected) previous.focus();
      else if (fallback?.isConnected) fallback.focus();
    };
  }, [fallbackFocusRef]);
  return (
    <dialog
      ref={dialog}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      aria-labelledby="document-delete-title"
      aria-describedby="document-delete-description"
      className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-[var(--border-default)] bg-[var(--surface)] p-0 text-[var(--text-primary)] shadow-2xl backdrop:bg-black/65 backdrop:backdrop-blur-sm"
    >
      <div className="border-b border-[var(--border-subtle)] px-6 py-5">
        <p className="mb-3 text-[10px] font-medium uppercase tracking-widest text-red-700 dark:text-red-400">
          Remove from knowledge base
        </p>
        <h2
          id="document-delete-title"
          className="text-[17px] font-semibold tracking-tight"
        >
          Delete document?
        </h2>
        <p className="mt-2 break-all text-[13px] font-medium">
          {document.filename}
        </p>
      </div>
      <div className="px-6 py-5">
        <p
          id="document-delete-description"
          className="text-[12px] leading-6 text-[var(--text-secondary)]"
        >
          This removes the original file and its indexed knowledge. Your
          workflows will no longer be able to use this document. This cannot be
          undone.
        </p>
        {error && (
          <p
            role="alert"
            className="mt-3 text-[12px] text-red-700 dark:text-red-400"
          >
            {error}
          </p>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <button
            ref={cancel}
            type="button"
            disabled={busy}
            onClick={onClose}
            className="h-9 rounded-[7px] border border-[var(--border-default)] px-3.5 text-[12px] font-medium hover:bg-[var(--elevated)] focus-visible:outline-2 focus-visible:outline-[var(--accent)] disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onDelete}
            className="h-9 rounded-[7px] bg-red-600 px-3.5 text-[12px] font-medium text-white hover:bg-red-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:opacity-50"
          >
            {busy ? "Deleting…" : "Delete document"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
