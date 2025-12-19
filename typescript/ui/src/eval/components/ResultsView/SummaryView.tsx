import { useMemo, useCallback } from "react";
import { Card, CardBody, CardHeader, Progress, Chip, ScrollShadow } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { selectProgress } from "../../stores/evalStore";

export function SummaryView() {
  const storeApi = useEvalStoreApi();
  const executions = useEvalStore((s) => s.executions);
  const progress = useMemo(() => selectProgress({ executions } as any), [executions]);

  const handleViewConversation = useCallback((scenarioName: string) => {
    const { selectScenario, setViewMode } = storeApi.getState().actions;
    selectScenario(scenarioName);
    setViewMode("conversation");
  }, [storeApi]);

  const executionList = Object.values(executions);

  if (executionList.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <Icon icon="heroicons:chart-bar" className="text-6xl text-foreground-300 mb-4" />
        <h2 className="text-lg font-medium text-foreground">No Results Yet</h2>
        <p className="text-sm text-foreground-500 mt-2">
          Run scenarios to see results here
        </p>
      </div>
    );
  }

  // Calculate aggregate metrics
  const totalTurns = executionList.reduce(
    (sum, e) => sum + e.turns.length,
    0,
  );
  const tasksCompleted = executionList.reduce(
    (sum, e) => sum + e.turns.filter((t) => t.task_completed).length,
    0,
  );

  return (
    <ScrollShadow className="h-full">
      <div className="p-6 space-y-6">
        {/* Overall Summary */}
        <Card>
        <CardHeader className="pb-2">
          <h3 className="text-lg font-semibold">Overall Progress</h3>
        </CardHeader>
        <CardBody className="gap-4">
          <Progress
            aria-label="Overall progress"
            value={progress.percentage}
            color={progress.failed > 0 ? "warning" : "primary"}
            showValueLabel
            className="max-w-full"
          />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-foreground">
                {progress.total}
              </p>
              <p className="text-xs text-foreground-500">Total Scenarios</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-success">
                {progress.completed}
              </p>
              <p className="text-xs text-foreground-500">Completed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-foreground">{totalTurns}</p>
              <p className="text-xs text-foreground-500">Total Turns</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-foreground">
                {tasksCompleted}
              </p>
              <p className="text-xs text-foreground-500">Tasks Completed</p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Scenario Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {executionList.map((execution) => (
          <Card
            key={execution.scenarioName}
            isPressable
            onPress={() => handleViewConversation(execution.scenarioName)}
            className="hover:border-primary transition-colors"
          >
            <CardBody className="gap-3">
              <div className="flex items-start justify-between">
                <h4 className="font-medium text-foreground truncate flex-1">
                  {execution.scenarioName}
                </h4>
                <StatusChip status={execution.status} />
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center gap-2 text-foreground-500">
                  <Icon icon="heroicons:chat-bubble-left-right" className="text-lg" />
                  <span>{execution.turns.length} turns</span>
                </div>
                <div className="flex items-center gap-2 text-foreground-500">
                  <Icon icon="heroicons:check" className="text-lg" />
                  <span>
                    {execution.turns.filter((t) => t.task_completed).length} tasks
                  </span>
                </div>
              </div>

              {/* Error */}
              {execution.error && (
                <p className="text-xs text-danger line-clamp-2">
                  {execution.error}
                </p>
              )}

              {/* Running indicator */}
              {execution.status === "running" && (
                <div className="flex items-center gap-2 text-xs text-primary">
                  <Icon icon="heroicons:arrow-path" className="animate-spin" />
                  <span>
                    Turn {execution.currentTurn} | Task{" "}
                    {execution.currentTaskIndex + 1}
                  </span>
                </div>
              )}
            </CardBody>
          </Card>
        ))}
        </div>
      </div>
    </ScrollShadow>
  );
}

function StatusChip({ status }: { status: string }) {
  const config: Record<string, { color: "default" | "primary" | "success" | "warning" | "danger"; label: string }> = {
    idle: { color: "default", label: "Idle" },
    queued: { color: "primary", label: "Queued" },
    running: { color: "primary", label: "Running" },
    completed: { color: "success", label: "Done" },
    failed: { color: "danger", label: "Failed" },
    timeout: { color: "warning", label: "Timeout" },
  };

  const { color, label } = config[status] ?? config.idle;

  return (
    <Chip size="sm" color={color} variant="flat">
      {label}
    </Chip>
  );
}
