"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { loginUser } from "@/services/auth";
import EmailVerificationModal from "@/components/auth/EmailVerificationModal";

export function isEmailValid(email = "") {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default function LoginForm() {
  const router = useRouter();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [touched, setTouched] = useState({
    email: false,
    password: false,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendError, setBackendError] = useState("");
  const [isUnverified, setIsUnverified] = useState(false);
  const [verificationModalOpen, setVerificationModalOpen] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (backendError) {
      setBackendError("");
      setIsUnverified(false);
    }
  };

  const handleBlur = (fieldName) => {
    setTouched((prev) => ({ ...prev, [fieldName]: true }));
  };

  // Field error calculations
  const emailError = touched.email
    ? !formData.email.trim()
      ? "Email is required."
      : !isEmailValid(formData.email)
      ? "Please enter a valid email address."
      : null
    : null;

  const passwordError = touched.password
    ? !formData.password
      ? "Password is required."
      : null
    : null;

  const isFormValid = Boolean(
    formData.email.trim() &&
      isEmailValid(formData.email) &&
      formData.password
  );

  const handleSubmit = async (e) => {
    e.preventDefault();

    setTouched({
      email: true,
      password: true,
    });

    if (!isFormValid || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setBackendError("");
    setIsUnverified(false);

    try {
      const response = await loginUser({
        email: formData.email.trim(),
        password: formData.password,
      });

      // Isolated token handling if tokens exist in response
      if (response?.access_token) {
        try {
          localStorage.setItem("access_token", response.access_token);
          if (response.refresh_token) {
            localStorage.setItem("refresh_token", response.refresh_token);
          }
        } catch {
          // Fallback if localStorage is restricted
        }
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
        lowerMsg.includes("verify") ||
        lowerMsg.includes("unverified") ||
        lowerMsg.includes("verification")
      ) {
        setIsUnverified(true);
        setVerificationEmail(formData.email.trim());
        setBackendError("Please verify your email before signing in.");
      } else if (
        lowerMsg.includes("invalid") ||
        lowerMsg.includes("credentials") ||
        lowerMsg.includes("incorrect") ||
        lowerMsg.includes("401") ||
        lowerMsg.includes("user not found")
      ) {
        setBackendError("Invalid email or password.");
      } else if (isNetworkOrDevError) {
        setBackendError("Unable to sign in right now. Please try again.");
      } else {
        setBackendError(msg || "Unable to sign in right now. Please try again.");
      }
    }
  };

  return (
    <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight">
          Welcome back
        </h1>
        <p className="mt-2 text-[15px] leading-[24px] text-[var(--text-secondary)]">
          Sign in to your Relay account.
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
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span className="leading-snug">{backendError}</span>
          </div>

          {/* Unverified Email Resend Action */}
          {isUnverified && (
            <div className="mt-3 pt-2.5 border-t border-red-500/20 text-left">
              <button
                type="button"
                onClick={() => setVerificationModalOpen(true)}
                className="text-[13px] font-semibold underline text-red-600 dark:text-red-300 hover:text-red-700 dark:hover:text-red-200 focus:outline-none focus:ring-1 focus:ring-red-400 rounded-[2px] cursor-pointer"
              >
                Resend verification email
              </button>
            </div>
          )}
        </div>
      )}

      {/* Login Form */}
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
            value={formData.email}
            onChange={handleChange}
            onBlur={() => handleBlur("email")}
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

        {/* Password Field */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="password"
              className="block text-[14px] font-medium text-[var(--text-secondary)]"
            >
              Password
            </label>
            <Link
              href="/forgot-password"
              className="text-[13px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:underline transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--accent)] rounded-[2px]"
            >
              Forgot password?
            </Link>
          </div>

          <div className="relative">
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              disabled={isSubmitting}
              value={formData.password}
              onChange={handleChange}
              onBlur={() => handleBlur("password")}
              placeholder="••••••••"
              aria-invalid={Boolean(passwordError)}
              aria-describedby={passwordError ? "password-error" : undefined}
              className={`w-full h-11 pl-3.5 pr-11 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
                passwordError
                  ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                  : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
              } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
            />

            {/* Password Visibility Toggle */}
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 rounded p-1 transition-colors duration-100 cursor-pointer disabled:opacity-50"
            >
              {showPassword ? (
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              ) : (
                <svg
                  className="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>

          {passwordError && (
            <p
              id="password-error"
              className="mt-1.5 text-[13px] text-red-500 dark:text-red-400"
            >
              {passwordError}
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
                <span>Signing in...</span>
              </>
            ) : (
              <span>Sign in</span>
            )}
          </button>
        </div>

        {/* Divider */}
        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[var(--border-subtle)]" />
          </div>
          <div className="relative flex justify-center text-[12px] uppercase">
            <span className="bg-[var(--surface)] px-2 text-[var(--text-tertiary)] font-medium">
              or
            </span>
          </div>
        </div>

        {/* Google SSO Button */}
        <div>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => {
              const authUrl = process.env.NEXT_PUBLIC_AUTH_API_URL;
              if (authUrl) {
                // eslint-disable-next-line @next/next/no-location-assign-relative-destination
                window.location.href = `${authUrl}/auth/google`;
              } else {
                router.push("/auth/google");
              }
            }}
            className="w-full h-11 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[var(--text-primary)] font-medium text-[15px] flex items-center justify-center gap-3 transition-all duration-100 ease-out cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>
        </div>
      </form>

      {/* Footer Link */}
      <div className="mt-7 text-center text-[14px] text-[var(--text-tertiary)]">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="text-[var(--accent)] dark:text-[var(--accent-hover)] hover:underline font-medium focus:outline-none focus:ring-1 focus:ring-[var(--accent)] rounded-[2px]"
        >
          Create an account
        </Link>
      </div>

      {/* Reusable Email Verification Modal */}
      <EmailVerificationModal
        open={verificationModalOpen}
        email={verificationEmail}
        onClose={() => setVerificationModalOpen(false)}
      />
    </div>
  );
}
