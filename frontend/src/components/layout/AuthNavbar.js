"use client";

import Link from "next/link";
import Image from "next/image";
import { useTheme } from "@/context/ThemeContext";

export default function AuthNavbar() {
  const { theme } = useTheme();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 w-full h-24 px-8 md:px-16 flex items-center justify-between bg-[var(--canvas)]">
      <Link href="/" className="flex items-center">
        {(theme === "light" || theme === "system") && (
          <Image
            src="/brand/relay/relay-dark.png"
            alt="Relay Logo"
            width={400}
            height={120}
            priority
            className={`h-20 md:h-24 w-auto object-contain ${
              theme === "system" ? "dark:hidden inline-block" : "inline-block"
            }`}
          />
        )}
        {(theme === "dark" || theme === "system") && (
          <Image
            src="/brand/relay/relay-light.png"
            alt="Relay Logo"
            width={400}
            height={120}
            priority
            className={`h-20 md:h-24 w-auto object-contain ${
              theme === "system" ? "hidden dark:inline-block" : "inline-block"
            }`}
          />
        )}
      </Link>
      <div>
        <Link
          href="/login"
          className="px-4 py-2 text-[14px] font-medium rounded-[6px] text-[var(--text-primary)] border border-[var(--border-default)] bg-[var(--surface)] hover:bg-[var(--elevated)] hover:border-[var(--border-strong)] transition-all duration-100 ease-out inline-flex items-center"
        >
          Log in
        </Link>
      </div>
    </header>
  );
}
