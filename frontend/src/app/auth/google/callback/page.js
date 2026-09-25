"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { exchangeGoogleLoginCode } from "@/services/auth";
import { useAuth } from "@/context/AuthContext";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get("code");

    if (!code) {
      setError("Google login code is missing.");
      return;
    }

    async function completeLogin() {
      try {
        const response = await exchangeGoogleLoginCode(code);

        await login(
          response.access_token,
          response.refresh_token
        );

        router.replace("/dashboard");
      } catch (error) {
        console.error("Google login failed:", error);
        setError("Google login could not be completed.");
      }
    }

    completeLogin();
  }, [searchParams, login, router]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-lg font-medium">
            Sign-in failed
          </h1>

          <p className="mt-2 text-sm text-neutral-500">
            {error}
          </p>

          <button
            type="button"
            onClick={() => router.replace("/login")}
            className="mt-6"
          >
            Back to login
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center">
      <p className="text-sm text-neutral-500">
        Signing you in...
      </p>
    </main>
  );
}