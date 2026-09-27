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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150 font-sans select-none"
    >
      <div className="w-full max-w-md bg-[var(--surface)] border border-[var(--border-default)] rounded-xl p-6 shadow-2xl text-left relative animate-in zoom-in-95 duration-150">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          disabled={isSubmitting}
          aria-label="Close dialog"
          className="absolute top-4 right-4 p-1 rounded-[6px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] transition-colors cursor-pointer disabled:opacity-50"
        >
          <XIcon className="w-4 h-4 stroke-[1.5]" />
        </button>

        {/* Modal Header with Icon Badge */}
        <div className="flex items-start gap-3.5 mb-5 pr-6">
          <div className="w-10 h-10 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--accent)] shrink-0 shadow-2xs">
            <WorkflowIcon className="w-5 h-5 stroke-[1.5]" />
          </div>
          <div>
            <h2
              id="create-workflow-title"
              className="text-[16px] font-semibold text-[var(--text-primary)] tracking-tight leading-snug"
            >
              Create workflow
            </h2>
            <p className="text-[13px] text-[var(--text-secondary)] mt-0.5 leading-normal">
              Create a workflow to automate your process.
            </p>
          </div>
        </div>

        {/* General API Error Banner */}
        {apiError && (
          <div className="mb-4 p-3 rounded-[6px] bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-[12px] flex items-center gap-2">
            <AlertCircleIcon className="w-4 h-4 stroke-[1.5] shrink-0" />
            <span>{apiError}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name Field */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="workflow-name-input"
                className="text-[12px] font-medium text-[var(--text-secondary)]"
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
              className={`w-full h-9 px-3 text-[13px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border transition-all duration-100 ease-out focus:outline-none ${
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
                className="text-[12px] font-medium text-[var(--text-secondary)]"
              >
                Description
              </label>
              <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                Optional
              </span>
            </div>

            <textarea
              id="workflow-description-input"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSubmitting}
              placeholder="What does this workflow do?"
              className="w-full p-2.5 text-[13px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-1 focus:ring-[var(--accent)] focus:outline-none transition-all duration-100 ease-out resize-none leading-relaxed"
            />
          </div>

          {/* Action Buttons */}
          <div className="pt-4 mt-2 border-t border-[var(--border-subtle)] flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="h-8 px-3.5 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[12px] font-medium text-[var(--text-primary)] transition-all duration-100 ease-out cursor-pointer disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isSubmitting}
              className="h-8 px-4 rounded-[6px] bg-[#4F46E5] hover:bg-[#6366F1] active:opacity-90 text-white font-medium text-[12px] transition-all duration-100 ease-out flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shadow-none"
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
        </form>
      </div>
    </div>
  );
}
