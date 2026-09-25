"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { exchangeGoogleLoginCode } from "@/services/auth";
import { useAuth } from "@/context/AuthContext";

const codePromiseMap = new Map();

function getExchangePromise(code) {
  if (!codePromiseMap.has(code)) {
    codePromiseMap.set(code, exchangeGoogleLoginCode(code));
  }
  return codePromiseMap.get(code);
}

function GoogleCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const code = searchParams.get("code");
  const [error, setError] = useState(() => (!code ? "Google login code is missing." : null));
  const hasExecutedRef = useRef(false);

  useEffect(() => {
    if (!code || hasExecutedRef.current) {
      return;
    }

    hasExecutedRef.current = true;

    async function handleExchange() {
      try {
        const response = await getExchangePromise(code);

        if (response?.access_token && response?.refresh_token) {
          await login(response.access_token, response.refresh_token);
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.href = "/dashboard";
        } else if (response?.signup_session_id || response?.session) {
          const sessionId = response.signup_session_id || response.session;
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.href = `/workspace-setup?session=${encodeURIComponent(sessionId)}`;
        } else if (response?.redirect_to) {
          window.location.href = response.redirect_to;
        } else {
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.href = "/dashboard";
        }
      } catch (err) {
        const msg = err?.message || "";
        const lowerMsg = msg.toLowerCase();

        const existingRefreshToken =
          typeof window !== "undefined" && localStorage.getItem("refresh_token");

        if (
          lowerMsg.includes("already been used") ||
          lowerMsg.includes("already used") ||
          lowerMsg.includes("session has already")
        ) {
          if (existingRefreshToken) {
            // eslint-disable-next-line @next/next/no-location-assign-relative-destination
            window.location.href = "/dashboard";
            return;
          }
          setError(
            "This Google login session has already been used. Please try signing in again."
          );
        } else if (lowerMsg.includes("expired") || lowerMsg.includes("invalid")) {
          if (existingRefreshToken) {
            // eslint-disable-next-line @next/next/no-location-assign-relative-destination
            window.location.href = "/dashboard";
            return;
          }
          setError(
            "Your Google login session has expired or is invalid. Please sign in again."
          );
        } else {
          setError(msg || "Google login could not be completed. Please try again.");
        }
      }
    }

    handleExchange();
  }, [code, login, router]);

  if (error) {
    return (
      <main className="min-h-screen w-full flex flex-col items-center justify-center p-4 sm:p-6 bg-[var(--canvas)] text-[var(--text-primary)]">
        <div className="w-full max-w-[440px] bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 text-center">
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
              <line x1="12" y1="8" x2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h1 className="text-[28px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
            Sign-in failed
          </h1>
          <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-8">
            {error}
          </p>
          <Link
            href="/login"
            className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer inline-flex"
          >
            Back to login
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen w-full flex items-center justify-center bg-[var(--canvas)] text-[var(--text-primary)]">
      <div className="flex items-center gap-3 text-[15px] text-[var(--text-secondary)]">
        <div className="w-5 h-5 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
        <span>Signing you in...</span>
      </div>
    </main>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen w-full flex items-center justify-center bg-[var(--canvas)] text-[var(--text-primary)]">
          <div className="flex items-center gap-3 text-[15px] text-[var(--text-secondary)]">
            <div className="w-5 h-5 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
            <span>Signing you in...</span>
          </div>
        </main>
      }
    >
      <GoogleCallbackContent />
    </Suspense>
  );
}