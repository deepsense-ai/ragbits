import { useThemeContext } from "../../core/contexts/ThemeContext/useThemeContext";
import { Theme } from "../../core/contexts/ThemeContext/ThemeContext";
import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import { ScenarioList } from "./ScenarioList/ScenarioList";
import { ExecutionToolbar } from "./ExecutionControl/ExecutionToolbar";
import { ResultsContainer } from "./ResultsView/ResultsContainer";

export function EvalDashboard() {
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
            <Icon icon={isDark ? "heroicons:sun" : "heroicons:moon"} className="text-xl" />
          </Button>
        </div>
      </header>

      {/* Execution Toolbar */}
      <ExecutionToolbar />

      {/* Main Content */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Panel - Scenario List */}
        <aside className="w-80 flex-shrink-0 border-r border-divider overflow-y-auto">
          <ScenarioList />
        </aside>

        {/* Main Panel - Results */}
        <main className="flex-1 min-h-0 overflow-hidden">
          <ResultsContainer />
        </main>
      </div>
    </div>
  );
}
