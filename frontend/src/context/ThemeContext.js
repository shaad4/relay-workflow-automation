"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("relay-theme");
        if (saved === "light" || saved === "dark" || saved === "system") {
          return saved;
        }
      } catch {
        // Fallback
      }
    }
    return "system";
  });

  const applyTheme = useCallback((mode) => {
    if (typeof window === "undefined") return;
    const root = document.documentElement;
    root.classList.remove("light", "dark");

    if (mode === "light") {
      root.classList.add("light");
    } else if (mode === "dark") {
      root.classList.add("dark");
    } else if (mode === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      if (prefersDark) {
        root.classList.add("dark");
      } else {
        root.classList.add("light");
      }
    }
  }, []);

  const setTheme = useCallback(
    (newTheme) => {
      setThemeState(newTheme);
      try {
        localStorage.setItem("relay-theme", newTheme);
      } catch {
        // Ignore write errors
      }
      applyTheme(newTheme);
    },
    [applyTheme]
  );

  useEffect(() => {
    applyTheme(theme);

    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => applyTheme("system");
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
  }, [theme, applyTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    return { theme: "system", setTheme: () => {} };
  }
  return context;
}
