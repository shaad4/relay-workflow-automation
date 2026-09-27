"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { createWorkflow } from "@/services/workflows";

function XIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
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

function PlusIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function AlertCircleIcon(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" {...props}>
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

export default function CreateWorkflowDialog({ open, onClose, onSuccess }) {
  const { accessToken } = useAuth();
  const router = useRouter();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [validationError, setValidationError] = useState("");
  const [apiError, setApiError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nameInputRef = useRef(null);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setName("");
      setDescription("");
      setValidationError("");
      setApiError("");
      setIsSubmitting(false);

      const timer = setTimeout(() => {
        if (nameInputRef.current) {
          nameInputRef.current.focus();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // Keyboard shortcut: Escape to close
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape" && !isSubmitting) {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, isSubmitting, onClose]);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError("");
    setApiError("");

    const trimmedName = name.trim();
    const trimmedDescription = description.trim();

    // Validation: Name required
    if (!trimmedName) {
      setValidationError("Workflow name is required.");
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: trimmedName,
        ...(trimmedDescription ? { description: trimmedDescription } : {}),
      };

      const res = await createWorkflow(accessToken, payload);

      // Extract generated workflow ID
      const createdId =
        res?.id ||
        res?.workflow_id ||
        res?.workflow?.id ||
        res?.data?.id;
      if (!createdId) throw new Error("The server created the workflow but did not return its ID.");

      // Notify parent & close modal
      if (onSuccess) onSuccess(res || { id: createdId, name: trimmedName });
      onClose();

      // Navigate to workflow builder page
      router.push(`/workflows/${createdId}`);
    } catch (err) {
      console.error("Workflow creation error:", err);
      setApiError(err?.message || "Unable to create workflow. Please try again.");
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-workflow-title"
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm animate-in fade-in duration-150 font-sans"
    >
      <div className="relative my-auto w-full max-w-lg overflow-hidden rounded-2xl border border-[var(--border-default)] bg-[var(--surface)] text-left shadow-2xl animate-in zoom-in-95 duration-150">
        <div className="h-1 w-full bg-gradient-to-r from-indigo-500 via-violet-500 to-sky-400" />
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={isSubmitting}
          aria-label="Close dialog"
          className="absolute right-4 top-4 z-10 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface)] p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-[var(--elevated)] hover:text-[var(--text-primary)] cursor-pointer disabled:opacity-50"
        >
          <XIcon className="w-4 h-4 stroke-[1.5]" />
        </button>

        {/* Modal Header with Icon Badge */}
        <div className="border-b border-[var(--border-subtle)] px-6 pb-5 pt-6 pr-14">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-500 shadow-sm">
              <WorkflowIcon className="h-6 w-6 stroke-[1.5]" />
            </div>
            <div>
              <h2
                id="create-workflow-title"
                className="text-[18px] font-semibold tracking-tight leading-snug text-[var(--text-primary)]"
              >
                Create a workflow
              </h2>
              <p className="mt-1 text-[13px] leading-5 text-[var(--text-secondary)]">
                Start with a name and a short description. You can add steps next.
              </p>
            </div>
          </div>
        </div>

        {/* General API Error Banner */}
        {apiError && (
          <div className="mx-6 mt-5 flex items-center gap-2.5 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-[12px] text-red-600 dark:text-red-400">
            <AlertCircleIcon className="w-4 h-4 stroke-[1.5] shrink-0" />
            <span>{apiError}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="space-y-5 px-6 py-5">
          {/* Name Field */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="workflow-name-input"
                className="text-[12px] font-semibold text-[var(--text-primary)]"
              >
                Name <span className="text-red-500">*</span>
              </label>
              <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                Required
              </span>
            </div>

            <input
              id="workflow-name-input"
              ref={nameInputRef}
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (validationError) setValidationError("");
              }}
              disabled={isSubmitting}
              placeholder="e.g. Order Processing"
              className={`w-full h-11 px-3.5 text-[14px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-xl border transition-all duration-100 ease-out focus:outline-none ${
                validationError
                  ? "border-red-500 focus:ring-1 focus:ring-red-500"
                  : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)]"
              }`}
            />
            {validationError && (
              <p className="mt-1.5 text-[12px] text-red-500 font-medium flex items-center gap-1">
                <AlertCircleIcon className="w-3.5 h-3.5 stroke-[1.5]" />
                <span>{validationError}</span>
              </p>
            )}
          </div>

          {/* Description Field */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="workflow-description-input"
                className="text-[12px] font-semibold text-[var(--text-primary)]"
              >
                Description
              </label>
              <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                Optional
              </span>
            </div>

            <textarea
              id="workflow-description-input"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSubmitting}
              placeholder="What does this workflow do?"
              className="w-full resize-y rounded-xl border border-[var(--border-default)] bg-[var(--input-bg)] p-3.5 text-[13px] leading-5 text-[var(--text-primary)] placeholder-[var(--text-disabled)] transition-all focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/20"
            />
          </div>

          {/* Action Buttons */}
          <div className="-mx-6 -mb-5 mt-1 flex items-center justify-between gap-3 border-t border-[var(--border-subtle)] bg-[var(--elevated)]/45 px-6 py-4">
            <p className="hidden text-[11px] text-[var(--text-tertiary)] sm:block">You can change these details later.</p>
            <div className="ml-auto flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="h-9 rounded-lg border border-[var(--border-default)] bg-[var(--surface)] px-4 text-[12px] font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--elevated)] disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-[var(--accent)] px-4 text-[12px] font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  <span>Creating...</span>
                </>
              ) : (
                <>
                  <PlusIcon className="w-3.5 h-3.5 stroke-[2]" />
                  <span>Create</span>
                </>
              )}
            </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
