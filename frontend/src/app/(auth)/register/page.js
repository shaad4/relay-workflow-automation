import AuthNavbar from "@/components/layout/AuthNavbar";
import RegisterForm from "@/components/auth/RegisterForm";

export const metadata = {
  title: "Create Account - Relay",
  description: "Create your Relay account and start building automated workflows.",
};

export default function RegisterPage() {
  return (
    <div className="min-h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-primary)]">
      {/* Top Navigation Bar */}
      <AuthNavbar />

      {/* Main Content Card Container */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 md:p-10 pt-28 md:pt-32">
        <RegisterForm />
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[12px] text-[var(--text-tertiary)] shrink-0">
        <p>Relay — Modern workflow automation platform.</p>
      </footer>
    </div>
  );
}
