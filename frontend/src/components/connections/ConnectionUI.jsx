"use client";

import { useEffect, useRef, useId } from "react";

export const inputClass =
  "h-9 w-full rounded-[6px] border border-[var(--border-default)] bg-[var(--input-bg)] px-3 text-[13px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-disabled)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)]/40 disabled:opacity-50";
export const buttonClass =
  "inline-flex h-9 items-center justify-center gap-1.5 rounded-[6px] border px-3 text-[13px] font-medium transition-colors duration-100 disabled:cursor-not-allowed disabled:opacity-50";
export const primaryClass = `${buttonClass} border-transparent bg-[var(--accent)] text-[var(--accent-foreground)] hover:bg-[var(--accent-hover)]`;
export const secondaryClass = `${buttonClass} border-[var(--border-default)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[var(--elevated)]`;

export function Modal({
  title,
  description,
  onClose,
  children,
  wide = false,
  className = "",
  hideTitle = false,
}) {
  const dialogRef = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const previous = document.activeElement;
    const dialog = dialogRef.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    (dialog.querySelector("input, select, button") || dialog).focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  useEffect(() => {
    const handleKey = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
      if (event.key === "Tab") {
        const controls = [
          ...dialogRef.current.querySelectorAll(
            'a[href], summary, button:not(:disabled), textarea:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]',
          ),
        ];
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (!first) {
          event.preventDefault();
          dialogRef.current.focus();
        } else if (
          event.shiftKey &&
          (document.activeElement === first ||
            !dialogRef.current.contains(document.activeElement))
        ) {
          event.preventDefault();
          last.focus();
        } else if (
          !event.shiftKey &&
          (document.activeElement === last ||
            !dialogRef.current.contains(document.activeElement))
        ) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);
  return (
    <div
      className="connection-overlay fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`connection-dialog max-h-[90vh] w-full ${wide ? "max-w-xl" : "max-w-md"} overflow-y-auto rounded-lg border border-[var(--border-default)] bg-[var(--surface)] p-5 ${className}`}
      >
        <div className="connection-dialog-header mb-5 flex items-start justify-between gap-4">
          <div className={hideTitle ? "sr-only" : undefined}>
            <h2 id={titleId} className="text-[18px] font-semibold">
              {title}
            </h2>
            {description && (
              <p className="mt-1 text-[13px] leading-5 text-[var(--text-secondary)]">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded p-1 text-[var(--text-tertiary)] transition-colors duration-100 hover:bg-[var(--elevated)]"
          >
            ×
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

export function Field({ label, htmlFor, error, helper, children }) {
  return (
    <div className="grid gap-1.5">
      <label
        htmlFor={htmlFor}
        className="text-[12px] font-medium text-[var(--text-secondary)]"
      >
        {label}
      </label>
      {children}
      {helper && (
        <p className="text-[11px] leading-4 text-[var(--text-tertiary)]">
          {helper}
        </p>
      )}
      {error && (
        <p role="alert" className="text-[12px] text-red-500">
          {error}
        </p>
      )}
    </div>
  );
}
