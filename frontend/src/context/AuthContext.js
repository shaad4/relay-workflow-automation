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
} from "@/services/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);

  async function login(accessToken, refresh_token) {
    setAccessToken(accessToken);

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
      const response = await refreshToken(storedRefreshToken);

      setAccessToken(response.access_token);

      const currentUser = await getCurrentUser(
        response.access_token
      );

      setUser(currentUser);
    } catch {
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

  function logout() {
    setAccessToken(null);
    setUser(null);

    localStorage.removeItem("refresh_token");
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