import {
  FC,
  ReactNode,
  useCallback,
  useMemo,
  useSyncExternalStore,
} from "react";
import { ThemeContext, Theme } from "./ThemeContext";

function getPreferredTheme() {
  const preferredDark = window.matchMedia(
    "(prefers-color-scheme: dark)",
  ).matches;

  document.documentElement.classList.toggle("dark", preferredDark);

  return preferredDark ? Theme.DARK : Theme.LIGHT;
}

function getSnapshot() {
  const saved = window.localStorage.getItem("theme");

  if (saved === Theme.DARK || saved === Theme.LIGHT) {
    document.documentElement.classList.toggle("dark", saved === Theme.DARK);
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
