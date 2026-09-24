import AuthNavbar from "@/components/layout/AuthNavbar";
import ForgotPasswordForm from "@/components/auth/ForgotPasswordForm";

export const metadata = {
  title: "Forgot Password - Relay",
  description: "Reset your Relay account password.",
};

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-primary)]">
      {/* Navigation Header */}
      <AuthNavbar />

      {/* Centered Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-10 pt-28 md:pt-32">
        <ForgotPasswordForm />
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[12px] text-[var(--text-tertiary)] shrink-0">
        <p>Relay — Modern workflow automation platform.</p>
      </footer>
    </div>
  );
}
