"use client";

import { Suspense } from "react";
import AuthNavbar from "@/components/layout/AuthNavbar";
import ResetPasswordForm from "@/components/auth/ResetPasswordForm";

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-primary)]">
      {/* Navigation Header */}
      <AuthNavbar />

      {/* Centered Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-10 pt-28 md:pt-32">
        <Suspense
          fallback={
            <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12 text-center">
              <div className="py-4">
                <div className="mx-auto w-12 h-12 rounded-[8px] bg-[var(--elevated)] border border-[var(--border-subtle)] flex items-center justify-center mb-6 text-[var(--text-primary)]">
                  <div className="w-5 h-5 border-2 border-[var(--text-secondary)] border-t-transparent rounded-full animate-spin" />
                </div>
                <h1 className="text-[24px] sm:text-[28px] leading-[34px] font-bold text-[var(--text-primary)] tracking-tight mb-2">
                  Loading reset password page...
                </h1>
              </div>
            </div>
          }
        >
          <ResetPasswordForm />
        </Suspense>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[12px] text-[var(--text-tertiary)] shrink-0">
        <p>Relay — Modern workflow automation platform.</p>
      </footer>
    </div>
  );
}
