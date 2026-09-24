"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { registerUser } from "@/services/auth";
import EmailVerificationModal from "@/components/auth/EmailVerificationModal";

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

export function isEmailValid(email = "") {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export default function RegisterForm() {
  const router = useRouter();

  const [step, setStep] = useState(1);

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    workspace_name: "",
    password: "",
    confirmPassword: "",
  });

  const [touched, setTouched] = useState({
    name: false,
    email: false,
    workspace_name: false,
    password: false,
    confirmPassword: false,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backendError, setBackendError] = useState("");
  const [verificationModalOpen, setVerificationModalOpen] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (backendError) setBackendError("");
  };

  const handleBlur = (fieldName) => {
    setTouched((prev) => ({ ...prev, [fieldName]: true }));
  };

  const passwordRequirements = getPasswordRequirements(formData.password);

  // Field validation checks
  const nameError =
    touched.name && !formData.name.trim()
      ? "Full name is required."
      : null;

  const emailError = touched.email
    ? !formData.email.trim()
      ? "Email is required."
      : !isEmailValid(formData.email)
      ? "Please enter a valid email address."
      : null
    : null;

  const workspaceNameError =
    touched.workspace_name && !formData.workspace_name.trim()
      ? "Workspace name is required."
      : null;

  const passwordError = touched.password
    ? !formData.password
      ? "Password is required."
      : !isPasswordValid(formData.password)
      ? "Password does not meet strength requirements."
      : null
    : null;

  const confirmPasswordError = touched.confirmPassword
    ? !formData.confirmPassword
      ? "Please confirm your password."
      : formData.confirmPassword !== formData.password
      ? "Passwords do not match."
      : null
    : null;

  const isStep1Valid = Boolean(
    formData.name.trim() && isEmailValid(formData.email)
  );
  const isStep2Valid = Boolean(formData.workspace_name.trim());
  const isStep3Valid = Boolean(
    isPasswordValid(formData.password) &&
      formData.confirmPassword === formData.password
  );

  const handleNextStep1 = (e) => {
    e.preventDefault();
    setTouched((prev) => ({ ...prev, name: true, email: true }));
    if (isStep1Valid) {
      setStep(2);
    }
  };

  const handleNextStep2 = (e) => {
    e.preventDefault();
    setTouched((prev) => ({ ...prev, workspace_name: true }));
    if (isStep2Valid) {
      setStep(3);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setTouched({
      name: true,
      email: true,
      workspace_name: true,
      password: true,
      confirmPassword: true,
    });

    if (!isStep1Valid) {
      setStep(1);
      return;
    }

    if (!isStep2Valid) {
      setStep(2);
      return;
    }

    if (!isStep3Valid || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setBackendError("");

    try {
      const response = await registerUser({
        name: formData.name.trim(),
        email: formData.email.trim(),
        password: formData.password,
        workspace_name: formData.workspace_name.trim(),
      });

      setIsSubmitting(false);
      setVerificationEmail(response?.email || formData.email.trim());
      setVerificationModalOpen(true);
    } catch (err) {
      const isNetworkOrDevError =
        !process.env.NEXT_PUBLIC_AUTH_API_URL ||
        err?.name === "TypeError" ||
        err?.message?.toLowerCase().includes("failed to fetch") ||
        err?.message?.toLowerCase().includes("networkerror");

      if (isNetworkOrDevError) {
        setIsSubmitting(false);
        setVerificationEmail(formData.email.trim());
        setVerificationModalOpen(true);
      } else {
        let message = "Unable to create your account. Please try again.";
        if (err?.message) {
          const rawMsg = err.message.toLowerCase();
          if (
            rawMsg.includes("email already registered") ||
            rawMsg.includes("already exists") ||
            rawMsg.includes("email taken")
          ) {
            message = "An account with this email already exists.";
            setStep(1);
          } else {
            message = err.message;
          }
        }
        setBackendError(message);
        setIsSubmitting(false);
      }
    }
  };

  return (
    <div className="w-full max-w-[520px] mx-auto bg-[var(--surface)] border border-[var(--border-subtle)] rounded-xl sm:rounded-2xl p-8 sm:p-10 md:p-12">
      {/* Progress Pills / Step Indicators */}
      <div className="flex items-center justify-center gap-2 mb-6">
        <span
          className={`h-1.5 rounded-full transition-all duration-300 ${
            step === 1
              ? "w-8 bg-[var(--text-primary)]"
              : "w-1.5 bg-[var(--border-strong)]"
          }`}
        />
        <span
          className={`h-1.5 rounded-full transition-all duration-300 ${
            step === 2
              ? "w-8 bg-[var(--text-primary)]"
              : "w-1.5 bg-[var(--border-strong)]"
          }`}
        />
        <span
          className={`h-1.5 rounded-full transition-all duration-300 ${
            step === 3
              ? "w-8 bg-[var(--text-primary)]"
              : "w-1.5 bg-[var(--border-strong)]"
          }`}
        />
      </div>

      {/* Backend Error Alert Banner */}
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

      {/* STEP 1: Personal Details (Name & Email) */}
      {step === 1 && (
        <div>
          <div className="text-center mb-8">
            <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight">
              Create your account
            </h1>
            <p className="mt-2 text-[15px] leading-[24px] text-[var(--text-secondary)]">
              Enter your personal details to get started.
            </p>
          </div>

          <form onSubmit={handleNextStep1} noValidate className="space-y-5">
            {/* Full Name */}
            <div>
              <label
                htmlFor="name"
                className="block text-[14px] font-medium text-[var(--text-secondary)] mb-2"
              >
                Full Name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                required
                disabled={isSubmitting}
                value={formData.name}
                onChange={handleChange}
                onBlur={() => handleBlur("name")}
                placeholder="Jane Doe"
                aria-invalid={Boolean(nameError)}
                aria-describedby={nameError ? "name-error" : undefined}
                className={`w-full h-11 px-3.5 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
                  nameError
                    ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                    : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
                } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
              />
              {nameError && (
                <p
                  id="name-error"
                  className="mt-1.5 text-[13px] text-red-500 dark:text-red-400"
                >
                  {nameError}
                </p>
              )}
            </div>

            {/* Email */}
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
                required
                disabled={isSubmitting}
                value={formData.email}
                onChange={handleChange}
                onBlur={() => handleBlur("email")}
                placeholder="jane@example.com"
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

            {/* Next Button */}
            <div className="pt-2">
              <button
                type="submit"
                className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Continue</span>
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
                onClick={() => {
                  const authUrl = process.env.NEXT_PUBLIC_AUTH_API_URL;
                  if (authUrl) {
                    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
                    window.location.href = `${authUrl}/auth/google`;
                  } else {
                    router.push("/auth/google");
                  }
                }}
                className="w-full h-11 px-4 rounded-[6px] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] text-[var(--text-primary)] font-medium text-[15px] flex items-center justify-center gap-3 transition-all duration-100 ease-out cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/30"
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
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-[var(--accent)] dark:text-[var(--accent-hover)] hover:underline font-medium focus:outline-none focus:ring-1 focus:ring-[var(--accent)] rounded-[2px]"
            >
              Log in
            </Link>
          </div>
        </div>
      )}

      {/* STEP 2: Workspace Setup */}
      {step === 2 && (
        <div>
          <div className="text-center mb-8">
            <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight">
              Name your workspace
            </h1>
            <p className="mt-2 text-[15px] leading-[24px] text-[var(--text-secondary)]">
              Workspaces keep your automated workflows organized.
            </p>
          </div>

          <form onSubmit={handleNextStep2} noValidate className="space-y-5">
            {/* Workspace Name */}
            <div>
              <label
                htmlFor="workspace_name"
                className="block text-[14px] font-medium text-[var(--text-secondary)] mb-2"
              >
                Workspace Name
              </label>
              <input
                id="workspace_name"
                name="workspace_name"
                type="text"
                required
                autoFocus
                disabled={isSubmitting}
                value={formData.workspace_name}
                onChange={handleChange}
                onBlur={() => handleBlur("workspace_name")}
                placeholder="Acme Corp"
                aria-invalid={Boolean(workspaceNameError)}
                aria-describedby={
                  workspaceNameError ? "workspace_name-error" : undefined
                }
                className={`w-full h-11 px-3.5 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
                  workspaceNameError
                    ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                    : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
                } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
              />
              {workspaceNameError && (
                <p
                  id="workspace_name-error"
                  className="mt-1.5 text-[13px] text-red-500 dark:text-red-400"
                >
                  {workspaceNameError}
                </p>
              )}
            </div>

            {/* Continue Button */}
            <div className="pt-2">
              <button
                type="submit"
                className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>Continue</span>
              </button>
            </div>

            {/* Back to Step 1 */}
            <div className="text-center pt-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="text-[14px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors duration-100 font-medium inline-flex items-center gap-1 cursor-pointer"
              >
                ← Back
              </button>
            </div>
          </form>
        </div>
      )}

      {/* STEP 3: Password & Confirm Password */}
      {step === 3 && (
        <div>
          <div className="text-center mb-8">
            <h1 className="text-[28px] sm:text-[32px] leading-[36px] font-bold text-[var(--text-primary)] tracking-tight">
              Set a secure password
            </h1>
            <p className="mt-2 text-[15px] leading-[24px] text-[var(--text-secondary)]">
              Choose a strong password to protect your account.
            </p>
          </div>

          <form onSubmit={handleSubmit} noValidate className="space-y-5">
            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-[14px] font-medium text-[var(--text-secondary)] mb-2"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoFocus
                  disabled={isSubmitting}
                  value={formData.password}
                  onChange={handleChange}
                  onFocus={() => setIsPasswordFocused(true)}
                  onBlur={() => {
                    setIsPasswordFocused(false);
                    handleBlur("password");
                  }}
                  placeholder="••••••••"
                  aria-invalid={Boolean(passwordError)}
                  aria-describedby={
                    isPasswordFocused || formData.password.length > 0
                      ? "password-requirements password-error"
                      : passwordError
                      ? "password-error"
                      : undefined
                  }
                  className={`w-full h-11 pl-3.5 pr-11 text-[15px] bg-[var(--input-bg)] text-[var(--text-primary)] placeholder-[var(--text-disabled)] rounded-[6px] border ${
                    passwordError
                      ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
                      : "border-[var(--border-default)] focus:border-[var(--border-strong)] focus:ring-[var(--accent)]/20"
                  } focus:outline-none focus:ring-2 transition-colors duration-100 ease-out disabled:opacity-50 disabled:cursor-not-allowed`}
                />
                <button
                  type="button"
                  tabIndex={0}
                  disabled={isSubmitting}
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-0 top-0 h-11 px-3.5 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] focus:outline-none focus:text-[var(--text-primary)] transition-colors duration-100 cursor-pointer"
                >
                  {showPassword ? (
                    <svg
                      className="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
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
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>

              {/* Password Requirements List — rendered dynamically when needed */}
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
                Confirm Password
              </label>
              <div className="relative">
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
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
                <button
                  type="button"
                  tabIndex={0}
                  disabled={isSubmitting}
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  aria-label={
                    showConfirmPassword ? "Hide password" : "Show password"
                  }
                  className="absolute right-0 top-0 h-11 px-3.5 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] focus:outline-none focus:text-[var(--text-primary)] transition-colors duration-100 cursor-pointer"
                >
                  {showConfirmPassword ? (
                    <svg
                      className="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
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
                      strokeWidth="2"
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

            {/* Final Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full h-11 px-4 rounded-[6px] bg-[#171717] dark:bg-[#EDEDED] text-white dark:text-black font-semibold text-[15px] hover:bg-black dark:hover:bg-white active:opacity-90 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/40 transition-all duration-100 ease-out flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    <span>Creating account...</span>
                  </>
                ) : (
                  <span>Create account</span>
                )}
              </button>
            </div>

            {/* Back to Step 2 */}
            <div className="text-center pt-2">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => setStep(2)}
                className="text-[14px] text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors duration-100 font-medium inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
              >
                ← Back
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Email Verification Modal */}
      <EmailVerificationModal
        open={verificationModalOpen}
        email={verificationEmail}
        onClose={() => setVerificationModalOpen(false)}
      />
    </div>
  );
}
