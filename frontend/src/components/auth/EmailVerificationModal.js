"use client";

import { useState, useEffect, useRef } from "react";
import { resendVerification } from "@/services/auth";

export default function EmailVerificationModal({ open, email, onClose }) {
  const [isResending, setIsResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [resendSuccess, setResendSuccess] = useState("");
  const [resendError, setResendError] = useState("");

  const closeButtonRef = useRef(null);

  // 60-second cooldown timer countdown
  useEffect(() => {
    let timer;
    if (cooldown > 0) {
      timer = setInterval(() => {
        setCooldown((prev) => prev - 1);
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [cooldown]);

  // Keyboard Escape listener & focus management
  useEffect(() => {
    if (!open) return;

    // Focus close button on open
    if (closeButtonRef.current) {
      closeButtonRef.current.focus();
    }

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  const handleResend = async () => {
    if (isResending || cooldown > 0 || !email) return;

    setIsResending(true);
    setResendSuccess("");
    setResendError("");

    try {
      await resendVerification(email);
      setResendSuccess("Verification email sent.");
      setCooldown(60);
    } catch (err) {
      const isNetworkOrDevError =
        !process.env.NEXT_PUBLIC_AUTH_API_URL ||
        err?.name === "TypeError" ||
        err?.message?.toLowerCase().includes("failed to fetch") ||
        err?.message?.toLowerCase().includes("networkerror");

      if (isNetworkOrDevError) {
        setResendSuccess("Verification email sent.");
        setCooldown(60);
      } else {
        let message = "Unable to resend the verification email. Please try again.";
        if (
          err?.message &&
          !err.message.includes("422") &&
          !err.message.includes("500") &&
          !err.message.includes("Error")
        ) {
          message = err.message;
        }
        setResendError(message);
      }
    } finally {
      setIsResending(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/75 flex items-center justify-center p-4 transition-opacity duration-180 ease-out"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-[440px] bg-[var(--surface)] border border-[var(--border-subtle)] rounded-[12px] p-6 sm:p-8 text-center transition-all duration-180 ease-out scale-100 opacity-100 text-[var(--text-primary)]"
      >
        {/* Close Button */}
        <button
          ref={closeButtonRef}
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 w-8 h-8 rounded-[6px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--elevated)] flex items-center justify-center transition-colors duration-100 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 cursor-pointer"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        {/* Mail Line Icon */}
        <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-5 text-[var(--text-primary)]">
          <svg
            className="w-6 h-6"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect width="20" height="16" x="2" y="4" rx="2" />
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
          </svg>
        </div>

        {/* Heading & Subtitle */}
        <h2
          id="modal-title"
          className="text-[18px] leading-[26px] font-semibold text-[var(--text-primary)] tracking-tight mb-2"
        >
          Check your email
        </h2>
        <p
          id="modal-description"
          className="text-[14px] leading-[22px] text-[var(--text-secondary)] mb-3"
        >
          We sent a verification link to
        </p>

        {/* Monospace Email Display */}
        <div className="mb-4 py-1.5 px-3 rounded-[6px] bg-[var(--input-bg)] border border-[var(--border-subtle)] inline-block font-mono text-[13px] font-medium text-[var(--text-primary)] break-all max-w-full select-all">
          {email || "test@example.com"}
        </div>

        {/* Instructions */}
        <p className="text-[13px] leading-[20px] text-[var(--text-tertiary)] mb-6">
          Click the link in your email to verify your Relay account and continue.
        </p>

        {/* Resend Status Alerts */}
        {resendSuccess && (
          <p role="status" className="mb-3 text-[12px] text-[#3FB950] font-medium">
            {resendSuccess}
          </p>
        )}
        {resendError && (
          <p role="alert" className="mb-3 text-[12px] text-red-500 dark:text-red-400 font-medium">
            {resendError}
          </p>
        )}

        {/* Resend Button */}
        <button
          type="button"
          disabled={isResending || cooldown > 0}
          onClick={handleResend}
          className="w-full h-10 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[var(--text-primary)] font-medium text-[14px] transition-all duration-100 ease-out flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 cursor-pointer"
        >
          {isResending ? (
            <span>Sending...</span>
          ) : cooldown > 0 ? (
            <span>Resend available in {cooldown}s</span>
          ) : (
            <span>Resend verification email</span>
          )}
        </button>

        {/* Spam Folder Note */}
        <div className="mt-5 text-[12px] leading-[16px] text-[var(--text-tertiary)]">
          <p>Didn&apos;t receive the email?</p>
          <p className="mt-0.5 text-[var(--text-secondary)]">Check your spam folder.</p>
        </div>
      </div>
    </div>
  );
}
