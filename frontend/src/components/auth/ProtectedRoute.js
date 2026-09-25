"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function ProtectedRoute({ children }) {
  const router = useRouter();

  const {
    accessToken,
    isInitializing,
  } = useAuth();

  useEffect(() => {
    if (!isInitializing && !accessToken) {
      router.replace("/login");
    }
  }, [isInitializing, accessToken, router]);

  if (isInitializing) {
    return null;
  }

  if (!accessToken) {
    return null;
  }

  return children;
}