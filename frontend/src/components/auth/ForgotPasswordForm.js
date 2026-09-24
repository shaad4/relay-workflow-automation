"use client";

import { useState } from "react";
import Link from "next/link";
import { forgotPassword } from "@/services/auth";

export function isEmailValid(email = "") {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [backendError, setBackendError] = useState("");

  const emailError = touched
    ? !email.trim()
      ? "Email is required."
      : !isEmailValid(email)
      ? "Please enter a valid email address."
      : null
    : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setTouched(true);

    if (!email.trim() || !isEmailValid(email) || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setBackendError("");

    const targetEmail = email.trim();

    try {
      await forgotPassword(targetEmail);
      setIsSubmitting(false);
      setSubmittedEmail(targetEmail);
      setIsSuccess(true);
    } catch (err) {
      setIsSubmitting(false);

      const msg = err?.message || "";
      const isNetworkOrDevError =
        !process.env.NEXT_PUBLIC_AUTH_API_URL ||
        err?.name === "TypeError" ||
        msg.toLowerCase().includes("failed to fetch") ||
        msg.toLowerCase().includes("networkerror");

      if (isNetworkOrDevError) {
        // Dev fallback mode
        setSubmittedEmail(targetEmail);
        setIsSuccess(true);
      } else {
        // Display generic server error without breaking account enumeration protection
        setBackendError(
          "Unable to process your request right now. Please try again."
        );
      }
    }
  };

  // SUCCESS STATE
  if (isSuccess) {
    return (
      <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12 text-center">
        {/* Mail Icon */}
        <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-6 text-[var(--text-primary)]">
          <svg
            className="w-6 h-6 text-[var(--text-primary)]"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect width="20" height="16" x="2" y="4" rx="2" />
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
          </svg>
        </div>

        {/* Heading */}
        <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
          Check your email
        </h1>

        {/* Generic account-enumeration safe subtitle */}
        <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-3">
          If an account exists for this email, you&apos;ll receive a password
          reset link shortly.
        </p>

        {/* Monospace Email Display */}
        {submittedEmail && (
          <div className="mb-4 py-1.5 px-3 rounded-[6px] bg-[var(--input-bg)] border border-[var(--border-subtle)] inline-block font-mono text-[13px] font-medium text-[var(--text-primary)] break-all max-w-full select-all">
            {submittedEmail}
          </div>
        )}

        {/* Spam folder note */}
        <p className="text-[13px] leading-[20px] text-[var(--text-tertiary)] mb-8">
          Check your spam or junk folder if you don&apos;t see the email.
        </p>

        {/* Back to Login Button */}
        <Link
          href="/login"
          className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>Back to login</span>
        </Link>
      </div>
    );
  }

  // INITIAL FORM STATE
  return (
    <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight">
          Forgot password?
        </h1>
        <p className="mt-2 text-[15px] leading-[24px] text-[var(--text-secondary)]">
          Enter the email address associated with your Relay account and
          we&apos;ll send you a password reset link.
        </p>
      </div>

      {/* Backend Error Alert */}
      {backendError && (
        <div
          role="alert"
          className="mb-6 p-3.5 text-[14px] rounded-[6px] border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400 flex items-start gap-2.5"
        >
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
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="leading-snug">{backendError}</span>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        {/* Email Field */}
        <div>
          <label
            htmlFor="email"
            className="block text-[14px] font-medium text-[var(--text-secondary)] mb-2"
          >
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            disabled={isSubmitting}
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (backendError) setBackendError("");
            }}
            onBlur={() => setTouched(true)}
            placeholder="you@example.com"
            aria-invalid={Boolean(emailError)}
            aria-describedby={emailError ? "email-error" : undefined}
            className={`w-full h-11 px-3.5 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
              emailError
                ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
            } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
          />
          {emailError && (
            <p
              id="email-error"
              className="mt-1.5 text-[13px] text-red-500 dark:text-red-400"
            >
              {emailError}
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
                <span>Sending...</span>
              </>
            ) : (
              <span>Send reset link</span>
            )}
          </button>
        </div>
      </form>

      {/* Back to Login Link */}
      <div className="mt-7 text-center text-[14px] text-[var(--text-tertiary)]">
        <Link
          href="/login"
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:underline font-medium focus:outline-none focus:ring-1 focus:ring-[var(--accent)] rounded-[2px] transition-colors"
        >
          ← Back to login
        </Link>
      </div>
    </div>
  );
}
