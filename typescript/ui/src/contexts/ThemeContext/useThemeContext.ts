import { useContext } from "react";
import { ThemeContext, IThemeContext } from "./ThemeContext";

export function useThemeContext(): IThemeContext {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error(
      "useThemeContext must be used within a ThemeContextProvider",
    );
  }
  return context;
}
