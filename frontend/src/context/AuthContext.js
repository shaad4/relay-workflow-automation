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

  async function login(accessToken, refresh_token) {
    setAccessToken(accessToken);
    localStorage.setItem("access_token", accessToken);

    localStorage.setItem("refresh_token", refresh_token);

    const currentUser = await getCurrentUser(accessToken);

    setUser(currentUser);
  }

  async function restoreSession() {
    const storedRefreshToken = localStorage.getItem("refresh_token");

    if (!storedRefreshToken) {
      return;
    }

    try {
      const response = await refreshToken();

      setAccessToken(response.access_token);
      localStorage.setItem("access_token", response.access_token);

      const currentUser = await getCurrentUser(
        response.access_token
      );

      setUser(currentUser);
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");

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
    const handleAccessToken = (event) => setAccessToken(event.detail);
    const handleSessionExpired = () => {
      localStorage.removeItem("access_token");
      setAccessToken(null);
      setUser(null);
    };
    window.addEventListener("relay:access-token", handleAccessToken);
    window.addEventListener("relay:session-expired", handleSessionExpired);
    return () => {
      window.removeEventListener("relay:access-token", handleAccessToken);
      window.removeEventListener("relay:session-expired", handleSessionExpired);
    };
  }, []);

  async function logout() {
    const token = accessToken;
    try {
      if (token) await logoutUser(token);
    } catch (error) {
      // Clear the local session even if the server cannot be reached.
      console.error("Server-side logout failed:", error);
    }
    setAccessToken(null);
    setUser(null);

    localStorage.removeItem("refresh_token");
    localStorage.removeItem("access_token");
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
