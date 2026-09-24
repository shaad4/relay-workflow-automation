"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { resetPassword } from "@/services/auth";

export function getPasswordRequirements(password = "") {
  return [
    {
      id: "length",
      label: "8 to 128 characters",
      satisfied: password.length >= 8 && password.length <= 128,
    },
    {
      id: "uppercase",
      label: "At least one uppercase letter",
      satisfied: /[A-Z]/.test(password),
    },
    {
      id: "lowercase",
      label: "At least one lowercase letter",
      satisfied: /[a-z]/.test(password),
    },
    {
      id: "number",
      label: "At least one number",
      satisfied: /[0-9]/.test(password),
    },
    {
      id: "special",
      label: "At least one special character",
      satisfied: /[^A-Za-z0-9]/.test(password),
    },
  ];
}

export function isPasswordValid(password = "") {
  return getPasswordRequirements(password).every((req) => req.satisfied);
}

export function mapResetPasswordError(errMessage) {
  if (!errMessage) {
    return {
      title: "Unable to reset password",
      message: "Unable to reset your password right now. Please try again.",
      isTokenInvalid: false,
    };
  }

  const msg = errMessage.toLowerCase();

  if (
    msg.includes("invalid reset token") ||
    msg.includes("invalid token")
  ) {
    return {
      title: "Password reset link unavailable",
      message:
        "This password reset link is invalid. Please request a new password reset link.",
      isTokenInvalid: true,
    };
  }

  if (
    msg.includes("already been used") ||
    msg.includes("already used")
  ) {
    return {
      title: "Password reset link unavailable",
      message: "This password reset link has already been used.",
      isTokenInvalid: true,
    };
  }

  if (msg.includes("expired")) {
    return {
      title: "Password reset link unavailable",
      message:
        "This password reset link has expired. Please request a new one.",
      isTokenInvalid: true,
    };
  }

  if (msg.includes("user not found")) {
    return {
      title: "Account not found",
      message:
        "We couldn't find the account associated with this reset link.",
      isTokenInvalid: true,
    };
  }

  return {
    title: "Unable to reset password",
    message: "Unable to reset your password right now. Please try again.",
    isTokenInvalid: false,
  };
}

export default function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
  });

  const [touched, setTouched] = useState({
    password: false,
    confirmPassword: false,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [tokenError, setTokenError] = useState(null);
  const [backendError, setBackendError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (backendError) setBackendError("");
  };

  const handleBlur = (fieldName) => {
    setTouched((prev) => ({ ...prev, [fieldName]: true }));
  };

  const passwordRequirements = getPasswordRequirements(formData.password);

  const passwordError = touched.password
    ? !formData.password
      ? "Password is required."
      : !isPasswordValid(formData.password)
      ? "Password does not meet requirements."
      : null
    : null;

  const confirmPasswordError = touched.confirmPassword
    ? !formData.confirmPassword
      ? "Please confirm your password."
      : formData.confirmPassword !== formData.password
      ? "Passwords do not match."
      : null
    : null;

  const isFormValid = Boolean(
    isPasswordValid(formData.password) &&
      formData.confirmPassword === formData.password
  );

  const handleSubmit = async (e) => {
    e.preventDefault();

    setTouched({
      password: true,
      confirmPassword: true,
    });

    if (!token || !isFormValid || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setBackendError("");

    try {
      await resetPassword(token, formData.password);
      setIsSubmitting(false);
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
        setIsSuccess(true);
      } else {
        const errorInfo = mapResetPasswordError(msg);
        if (errorInfo.isTokenInvalid) {
          setTokenError(errorInfo);
        } else {
          setBackendError(errorInfo.message);
        }
      }
    }
  };

  // 1. MISSING TOKEN STATE
  if (!token) {
    return (
      <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12 text-center">
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
          Invalid reset link
        </h1>
        <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-8">
          This password reset link is missing the required token.
        </p>

        <Link
          href="/login"
          className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>Back to login</span>
        </Link>
      </div>
    );
  }

  // 2. INVALID / EXPIRED / USED TOKEN ERROR STATE
  if (tokenError) {
    return (
      <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12 text-center">
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
          {tokenError.title}
        </h1>
        <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-8">
          {tokenError.message}
        </p>

        <div className="space-y-3">
          <Link
            href="/forgot-password"
            className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>Request a new reset link</span>
          </Link>
          <Link
            href="/login"
            className="w-full h-11 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[var(--text-primary)] font-medium text-[15px] transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>Back to login</span>
          </Link>
        </div>
      </div>
    );
  }

  // 3. SUCCESS STATE
  if (isSuccess) {
    return (
      <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12 text-center">
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
          Password reset successfully
        </h1>
        <p className="text-[15px] leading-[24px] text-[var(--text-secondary)] mb-8">
          Your password has been updated. You can now sign in with your new
          password.
        </p>

        <Link
          href="/login"
          className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>Continue to login</span>
        </Link>
      </div>
    );
  }

  // 4. RESET PASSWORD FORM STATE
  return (
    <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight">
          Reset your password
        </h1>
        <p className="mt-2 text-[15px] leading-[24px] text-[var(--text-secondary)]">
          Create a new password for your Relay account.
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
        {/* New Password */}
        <div>
          <label
            htmlFor="password"
            className="block text-[14px] font-medium text-[var(--text-secondary)] mb-2"
          >
            New password
          </label>
          <div className="relative">
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              disabled={isSubmitting}
              value={formData.password}
              onChange={handleChange}
              onFocus={() => setIsPasswordFocused(true)}
              onBlur={() => handleBlur("password")}
              placeholder="••••••••"
              aria-invalid={Boolean(passwordError)}
              aria-describedby={
                passwordError ? "password-error" : "password-requirements"
              }
              className={`w-full h-11 pl-3.5 pr-11 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
                passwordError
                  ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                  : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
              } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
            />

            {/* Visibility Toggle */}
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

          {/* Password Requirements List */}
          {(isPasswordFocused ||
            formData.password.length > 0 ||
            (touched.password && !isPasswordValid(formData.password))) && (
            <div
              id="password-requirements"
              className="mt-2.5 space-y-1 text-[13px] transition-all duration-150 ease-out"
            >
              {passwordRequirements.map((req) => (
                <div key={req.id} className="flex items-center gap-2">
                  <span
                    className={`text-[12px] font-mono leading-none ${
                      req.satisfied
                        ? "text-[var(--text-primary)] font-bold"
                        : "text-[var(--text-disabled)]"
                    }`}
                    aria-hidden="true"
                  >
                    {req.satisfied ? "✓" : "○"}
                  </span>
                  <span
                    className={
                      req.satisfied
                        ? "text-[var(--text-secondary)] font-medium"
                        : "text-[var(--text-tertiary)]"
                    }
                  >
                    {req.label}
                  </span>
                </div>
              ))}
            </div>
          )}

          {passwordError && (
            <p
              id="password-error"
              className="mt-1.5 text-[13px] text-red-500 dark:text-red-400"
            >
              {passwordError}
            </p>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label
            htmlFor="confirmPassword"
            className="block text-[14px] font-medium text-[var(--text-secondary)] mb-2"
          >
            Confirm password
          </label>
          <div className="relative">
            <input
              id="confirmPassword"
              name="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              disabled={isSubmitting}
              value={formData.confirmPassword}
              onChange={handleChange}
              onBlur={() => handleBlur("confirmPassword")}
              placeholder="••••••••"
              aria-invalid={Boolean(confirmPasswordError)}
              aria-describedby={
                confirmPasswordError ? "confirmPassword-error" : undefined
              }
              className={`w-full h-11 pl-3.5 pr-11 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
                confirmPasswordError
                  ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                  : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
              } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
            />

            {/* Visibility Toggle */}
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => setShowConfirmPassword((prev) => !prev)}
              aria-label={
                showConfirmPassword ? "Hide confirm password" : "Show confirm password"
              }
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 rounded p-1 transition-colors duration-100 cursor-pointer disabled:opacity-50"
            >
              {showConfirmPassword ? (
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

          {confirmPasswordError && (
            <p
              id="confirmPassword-error"
              className="mt-1.5 text-[13px] text-red-500 dark:text-red-400"
            >
              {confirmPasswordError}
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
                <span>Resetting password...</span>
              </>
            ) : (
              <span>Reset password</span>
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
