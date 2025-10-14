import {
  FC,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useSyncExternalStore,
  useRef,
} from "react";
import { RagbitsClient } from "@ragbits/api-client-react";
import { ThemeContext, Theme } from "./ThemeContext";
import { API_URL } from "../../../config";

function getPreferredTheme() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? Theme.DARK
    : Theme.LIGHT;
}

function getSnapshot() {
  const saved = window.localStorage.getItem("theme");
  if (saved === Theme.DARK || saved === Theme.LIGHT) {
    return saved;
  }
  return getPreferredTheme();
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

export const ThemeContextProvider: FC<{ children: ReactNode }> = ({
  children,
}) => {
  const themeValue = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const themeLoadedRef = useRef(false);
  const client = new RagbitsClient({
    baseUrl: API_URL,
  });

  // Load HeroUI custom theme from backend - only once
  useEffect(() => {
    if (themeLoadedRef.current) {
      return; // Already loaded, don't load again
    }

    const loadCustomTheme = async () => {
      try {
        // Use the client's internal _makeRequest or build the URL manually
        const baseUrl = client.getBaseUrl();
        const response = await fetch(`${baseUrl}/api/theme`);

        if (response.ok) {
          const cssContent = await response.text();

          // Remove existing custom theme
          const existingTheme = document.getElementById("heroui-custom-theme");
          if (existingTheme) {
            existingTheme.remove();
          }

          // // Create and inject new custom theme
          const style = document.createElement("style");
          style.id = "heroui-custom-theme";
          style.textContent = cssContent;
          document.head.appendChild(style);

          console.log("Custom HeroUI theme loaded successfully");
          themeLoadedRef.current = true; // Mark as loaded
        }
      } catch (error) {
        console.warn("No custom theme available:", error);
        themeLoadedRef.current = true; // Mark as attempted to prevent retries
      }
    };

    loadCustomTheme();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array - only run once on mount

  // Handle light/dark mode switching
  useEffect(() => {
    document.documentElement.classList.toggle(
      "dark",
      themeValue === Theme.DARK,
    );
  }, [themeValue]);

  const setTheme = useCallback((newTheme: Theme) => {
    window.localStorage.setItem("theme", newTheme);
    window.dispatchEvent(new Event("storage"));
  }, []);

  const value = useMemo(
    () => ({
      theme: themeValue as Theme,
      setTheme,
    }),
    [themeValue, setTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
};
