"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function PublicRoute({ children }) {
  const router = useRouter();

  const {
    accessToken,
    isInitializing,
  } = useAuth();

  useEffect(() => {
    if (!isInitializing && accessToken) {
      router.replace("/dashboard");
    }
  }, [isInitializing, accessToken, router]);

  if (isInitializing) {
    return null;
  }

  if (accessToken) {
    return null;
  }

  return children;
}