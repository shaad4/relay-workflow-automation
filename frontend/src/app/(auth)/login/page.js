import AuthNavbar from "@/components/layout/AuthNavbar";
import LoginForm from "@/components/auth/LoginForm";

export const metadata = {
  title: "Log In - Relay",
  description: "Sign in to your Relay account.",
};

export default function LoginPage() {
  return (
    <div className="min-h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-primary)]">
      {/* Navigation Header */}
      <AuthNavbar />

      {/* Centered Main Content Area */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-10 pt-28 md:pt-32">
        <LoginForm />
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[12px] text-[var(--text-tertiary)] shrink-0">
        <p>Relay — Modern workflow automation platform.</p>
      </footer>
    </div>
  );
}
