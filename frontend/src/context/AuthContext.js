"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  refreshToken,
  getCurrentUser,
  logoutUser,
} from "@/services/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);

  async function login() {
    const currentUser = await getCurrentUser();

    setAccessToken(true);
    setUser(currentUser);
  }

  async function restoreSession() {
    try {
      await refreshToken();
      const currentUser = await getCurrentUser();

      setAccessToken(true);
      setUser(currentUser);
    } catch {
      setAccessToken(null);
      setUser(null);
    }
  }

  useEffect(() => {
    async function initializeAuth() {
      try {
        await restoreSession();
      } finally {
        setIsInitializing(false);
      }
    }

    initializeAuth();
  }, []);

  useEffect(() => {
    const handleSessionExpired = () => {
      setAccessToken(null);
      setUser(null);
    };
    window.addEventListener("relay:session-expired", handleSessionExpired);
    return () => {
      window.removeEventListener("relay:session-expired", handleSessionExpired);
    };
  }, []);

  async function logout() {
    try {
      if (accessToken) await logoutUser();
    } catch (error) {
      // Clear the local session even if the server cannot be reached.
      console.error("Server-side logout failed:", error);
    }
    setAccessToken(null);
    setUser(null);

  }

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        user,
        login,
        logout,
        restoreSession,
        setUser,
        isInitializing,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider"
    );
  }

  return context;
}
