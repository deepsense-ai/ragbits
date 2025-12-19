import { Outlet } from "react-router";
import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useThemeContext } from "../../core/contexts/ThemeContext/useThemeContext";
import { Theme } from "../../core/contexts/ThemeContext/ThemeContext";
import { EvalTabs } from "./EvalTabs";

export function EvalLayout() {
  const { theme, setTheme } = useThemeContext();
  const isDark = theme === Theme.DARK;
  const toggleTheme = () => setTheme(isDark ? Theme.LIGHT : Theme.DARK);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-divider px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🧪</span>
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              Ragbits Evaluation
            </h1>
            <p className="text-xs text-foreground-500">
              Test scenarios and view results
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            isIconOnly
            variant="light"
            onPress={toggleTheme}
            aria-label="Toggle theme"
          >
            <Icon
              icon={isDark ? "heroicons:sun" : "heroicons:moon"}
              className="text-xl"
            />
          </Button>
        </div>
      </header>

      {/* Tab Navigation */}
      <EvalTabs />

      {/* Main Content */}
      <main className="flex-1 min-h-0 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
