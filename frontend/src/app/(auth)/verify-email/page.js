"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { verifyEmail } from "@/services/auth";
import AuthNavbar from "@/components/layout/AuthNavbar";

export function mapVerificationError(errMessage, hasToken) {
  if (!hasToken) {
    return "This verification link is missing the required token.";
  }

  if (!errMessage) {
    return "Something went wrong while verifying your email. Please try again.";
  }

  const msg = errMessage.toLowerCase();

  if (msg.includes("already been used") || msg.includes("already verified")) {
    return "This email address has already been verified.";
  }

  if (
    msg.includes("invalid verification token") ||
    msg.includes("invalid token")
  ) {
    return "This verification link is invalid. Please request a new verification email.";
  }

  if (msg.includes("expired")) {
    return "This verification link has expired. Please request a new verification email.";
  }

  if (msg.includes("user not found")) {
    return "We couldn't find the account associated with this verification link.";
  }

  return "Something went wrong while verifying your email. Please try again.";
}

const verificationCache = new Map();

function verifyEmailOnce(token) {
  if (!verificationCache.has(token)) {
    const promise = verifyEmail(token);
    verificationCache.set(token, promise);
  }
  return verificationCache.get(token);
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState(token ? "verifying" : "error");
  const [errorMessage, setErrorMessage] = useState(
    token ? "" : mapVerificationError(null, false)
  );

  useEffect(() => {
    if (!token) return;

    let isSubscribed = true;

    verifyEmailOnce(token)
      .then(() => {
        if (isSubscribed) {
          setStatus("success");
        }
      })
      .catch((err) => {
        if (!isSubscribed) return;

        const msg = err?.message || "";
        const isNetworkOrDevError =
          !process.env.NEXT_PUBLIC_AUTH_API_URL ||
          err?.name === "TypeError" ||
          msg.toLowerCase().includes("failed to fetch") ||
          msg.toLowerCase().includes("networkerror");

        if (isNetworkOrDevError) {
          setStatus("success");
        } else {
          setStatus("error");
          setErrorMessage(mapVerificationError(msg, true));
        }
      });

    return () => {
      isSubscribed = false;
    };
  }, [token]);

  return (
    <div className="w-full max-w-[440px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 text-center">
      {/* State A: VERIFYING */}
      {status === "verifying" && (
        <div aria-live="polite" className="py-2">
          <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-6 text-[var(--text-primary)]">
            <svg
              className="w-6 h-6 animate-spin text-[var(--text-secondary)]"
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
          </div>
          <h1 className="text-[24px] sm:text-[28px] leading-[34px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
            Verifying your email
          </h1>
          <p className="text-[15px] leading-[24px] text-[var(--text-secondary)]">
            Please wait while we verify your email address.
          </p>
        </div>
      )}

      {/* State B: SUCCESS */}
      {status === "success" && (
        <div className="py-2">
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
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
            Email verified
          </h1>
          <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-2">
            Your email address has been verified successfully.
          </p>
          <p className="text-[13px] leading-[20px] text-[var(--text-tertiary)] mb-8">
            You can now sign in to your Relay account.
          </p>
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>Continue to login</span>
          </button>
        </div>
      )}

      {/* State C: ERROR */}
      {status === "error" && (
        <div className="py-2">
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
            Unable to verify email
          </h1>
          <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-8">
            {errorMessage}
          </p>
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => router.push("/login")}
              className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Go to login</span>
            </button>
            <button
              type="button"
              onClick={() => router.push("/register")}
              className="w-full h-11 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[var(--text-primary)] font-medium text-[15px] transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Return to registration</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-primary)]">
      {/* Navigation Header */}
      <AuthNavbar />

      {/* Centered Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-10 pt-28 md:pt-32">
        <Suspense
          fallback={
            <div className="w-full max-w-[440px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 text-center">
              <div className="py-2">
                <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-6 text-[var(--text-primary)]">
                  <div className="w-5 h-5 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
                </div>
                <h1 className="text-[24px] sm:text-[28px] leading-[34px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
                  Verifying your email
                </h1>
                <p className="text-[15px] leading-[24px] text-[var(--text-secondary)]">
                  Please wait while we verify your email address.
                </p>
              </div>
            </div>
          }
        >
          <VerifyEmailContent />
        </Suspense>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[12px] text-[var(--text-tertiary)] shrink-0">
        <p>Relay — Modern workflow automation platform.</p>
      </footer>
    </div>
  );
}
