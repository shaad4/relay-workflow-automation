"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { completeGoogleSignup } from "@/services/auth";
import { useAuth } from "@/context/AuthContext";
import PublicRoute from "@/components/auth/PublicRoute";
import AuthNavbar from "@/components/layout/AuthNavbar";

function WorkspaceSetupContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login } = useAuth();

  const session = searchParams.get("session");

  const [workspaceName, setWorkspaceName] = useState("");
  const [touched, setTouched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendError, setBackendError] = useState("");

  const trimmedName = workspaceName.trim();

  const getValidationError = () => {
    if (!trimmedName || trimmedName.length < 2) {
      return "Please enter a workspace name.";
    }
    if (trimmedName.length > 100) {
      return "Workspace name must be 100 characters or fewer.";
    }
    return null;
  };

  const validationError = touched ? getValidationError() : null;

  const handleChange = (e) => {
    setWorkspaceName(e.target.value);
    if (backendError) {
      setBackendError("");
    }
  };

  const handleBlur = () => {
    setTouched(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);

    const error = getValidationError();
    if (error || isSubmitting || !session) {
      return;
    }

    setIsSubmitting(true);
    setBackendError("");

    try {
      const response = await completeGoogleSignup(session, trimmedName);

      if (response?.access_token && response?.refresh_token) {
        await login(response.access_token, response.refresh_token);
      }

      setIsSubmitting(false);
      router.push("/dashboard");
    } catch (err) {
      setIsSubmitting(false);

      const msg = err?.message || "";
      const lowerMsg = msg.toLowerCase();

      const isNetworkOrDevError =
        !process.env.NEXT_PUBLIC_AUTH_API_URL ||
        err?.name === "TypeError" ||
        lowerMsg.includes("failed to fetch") ||
        lowerMsg.includes("networkerror");

      if (
        lowerMsg.includes("expired") ||
        lowerMsg.includes("invalid session") ||
        lowerMsg.includes("signup session") ||
        lowerMsg.includes("session invalid")
      ) {
        setBackendError(
          "Your workspace setup session has expired. Please sign in with Google again."
        );
      } else if (isNetworkOrDevError) {
        setBackendError("Something went wrong. Please try again.");
      } else {
        setBackendError(msg || "Something went wrong. Please try again.");
      }
    }
  };

  // Missing or Invalid Session State
  if (!session) {
    return (
      <div className="w-full max-w-[440px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 text-center">
        <div className="mx-auto w-12 h-12 rounded-[8px] bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6 text-red-500 dark:text-red-400">
          <svg
            className="w-6 h-6"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
          Invalid Session
        </h1>
        <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-8">
          This workspace setup session is invalid or missing.
        </p>
        <Link
          href="/login"
          className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer inline-flex"
        >
          <span>Back to login</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[440px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight">
          Create your workspace
        </h1>
        <p className="mt-2 text-[15px] leading-[24px] text-[var(--text-secondary)]">
          Set up your workspace to get started with Relay.
        </p>
      </div>

      {/* Backend Error Alert Banner */}
      {backendError && (
        <div
          role="alert"
          className="mb-6 p-3.5 text-[14px] rounded-[6px] border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400"
        >
          <div className="flex items-start gap-2.5">
            <svg
              className="w-4 h-4 shrink-0 mt-0.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span className="leading-snug">{backendError}</span>
          </div>
        </div>
      )}

      {/* Workspace Form */}
      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* Workspace Name Field */}
        <div>
          <label
            htmlFor="workspaceName"
            className="block text-[14px] font-medium text-[var(--text-secondary)] mb-2"
          >
            Workspace name
          </label>
          <input
            id="workspaceName"
            name="workspaceName"
            type="text"
            required
            maxLength={110}
            disabled={isSubmitting}
            value={workspaceName}
            onChange={handleChange}
            onBlur={handleBlur}
            placeholder="My Company"
            aria-invalid={Boolean(validationError)}
            aria-describedby={
              validationError ? "workspaceName-error" : "workspaceName-helper"
            }
            className={`w-full h-11 px-3.5 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
              validationError
                ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
            } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
          />

          {validationError ? (
            <p
              id="workspaceName-error"
              className="mt-1.5 text-[13px] text-red-500 dark:text-red-400"
            >
              {validationError}
            </p>
          ) : (
            <p
              id="workspaceName-helper"
              className="mt-1.5 text-[13px] text-[var(--text-tertiary)]"
            >
              Your workspace is where your workflows and automation live.
            </p>
          )}
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <svg
                  className="w-4 h-4 animate-spin text-current"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="3"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Creating workspace...</span>
              </>
            ) : (
              <span>Create workspace</span>
            )}
          </button>
        </div>
      </form>

      {/* Secondary Navigation */}
      <div className="mt-7 text-center">
        <Link
          href="/login"
          className="text-[14px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:underline font-medium focus:outline-none focus:ring-1 focus:ring-[var(--accent)] rounded-[2px] transition-colors"
        >
          Back to login
        </Link>
      </div>
    </div>
  );
}

export default function WorkspaceSetupPage() {
  return (
    <div className="min-h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-primary)]">
      {/* Navigation Header */}
      <AuthNavbar />

      {/* Centered Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-10 pt-28 md:pt-32">
        <PublicRoute>
          <Suspense
            fallback={
              <div className="w-full max-w-[440px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 text-center">
                <div className="py-2">
                  <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-6 text-[var(--text-primary)]">
                    <div className="w-5 h-5 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
                  </div>
                  <h1 className="text-[24px] sm:text-[28px] leading-[34px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
                    Loading workspace setup...
                  </h1>
                </div>
              </div>
            }
          >
            <WorkspaceSetupContent />
          </Suspense>
        </PublicRoute>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[12px] text-[var(--text-tertiary)] shrink-0">
        <p>Relay — Modern workflow automation platform.</p>
      </footer>
    </div>
  );
}
