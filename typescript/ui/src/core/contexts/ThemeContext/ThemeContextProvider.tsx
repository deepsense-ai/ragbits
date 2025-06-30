import {
  FC,
  ReactNode,
  useCallback,
  useMemo,
  useSyncExternalStore,
} from "react";
import { ThemeContext, Theme } from "./ThemeContext";

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
