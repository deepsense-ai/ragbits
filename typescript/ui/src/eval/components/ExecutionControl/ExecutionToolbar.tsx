import { useMemo, useCallback } from "react";
import { Button, Progress, Chip } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { selectProgress, isPersonaScenario } from "../../stores/evalStore";
import { SimulationSettingsPopover } from "./SimulationSettingsPopover";
import type { ProgressUpdate } from "../../types";

export function ExecutionToolbar() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const config = useEvalStore((s) => s.config);
  const isExecuting = useEvalStore((s) => s.isExecuting);
  const executions = useEvalStore((s) => s.executions);
  const selectedForRun = useEvalStore((s) => s.selectedForRun);
  const progress = useMemo(() => selectProgress({ executions } as any), [executions]);

  // Get runnable scenarios (non-personas)
  const runnableScenarios = useMemo(() => {
    if (!config) return [];
    return config.available_scenarios
      .filter((s) => !isPersonaScenario(s.num_tasks))
      .map((s) => s.name);
  }, [config]);

  const runScenarios = useCallback(async (scenarioNames: string[]) => {
    const currentIsExecuting = storeApi.getState().isExecuting;
    const currentSimulationConfig = storeApi.getState().simulationConfig;

    if (scenarioNames.length === 0 || currentIsExecuting) return;

    try {
      // Start the evaluation run
      const response = await fetch(
        `${client.getBaseUrl()}/api/eval/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario_names: scenarioNames,
            config: currentSimulationConfig,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(`Failed to start evaluation: ${response.statusText}`);
      }

      const data = await response.json();
      const runId = data.run_id;

      // Initialize execution state
      storeApi.getState().actions.startExecution(runId, scenarioNames);

      // Connect to SSE stream for progress updates
      const eventSource = new EventSource(
        `${client.getBaseUrl()}/api/eval/progress/${runId}`,
      );

      eventSource.onmessage = (event) => {
        try {
          const update: ProgressUpdate = JSON.parse(event.data);
          storeApi.getState().actions.handleProgressUpdate(update);

          // Close the connection when all scenarios are complete
          if (update.type === "complete" || update.type === "error") {
            const currentProgress = selectProgress(storeApi.getState());
            if (currentProgress.running === 0) {
              eventSource.close();
            }
          }
        } catch (error) {
          console.error("Failed to parse progress update:", error);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
      };
    } catch (error) {
      console.error("Failed to start evaluation:", error);
    }
  }, [client, storeApi]);

  const handleRunSelected = useCallback(() => {
    const currentSelectedForRun = storeApi.getState().selectedForRun;
    runScenarios(currentSelectedForRun);
  }, [runScenarios, storeApi]);

  const handleRunAll = useCallback(() => {
    runScenarios(runnableScenarios);
  }, [runScenarios, runnableScenarios]);

  const handleStop = useCallback(() => {
    storeApi.getState().actions.stopExecution();
  }, [storeApi]);

  const handleClear = useCallback(() => {
    storeApi.getState().actions.clearExecutions();
  }, [storeApi]);

  const hasScenarios = runnableScenarios.length > 0;
  const hasSelectedScenarios = selectedForRun.length > 0;
  const hasExecutions = progress.total > 0;

  return (
    <div className="flex items-center justify-between gap-4 border-b border-divider px-6 py-3">
      {/* Progress Summary */}
      <div className="flex items-center gap-4 flex-1">
        {hasExecutions ? (
          <>
            <Progress
              aria-label="Execution progress"
              value={progress.percentage}
              className="max-w-xs"
              color={progress.failed > 0 ? "warning" : "primary"}
              size="sm"
            />
            <div className="flex items-center gap-2">
              {progress.completed > 0 && (
                <Chip size="sm" color="success" variant="flat">
                  {progress.completed} completed
                </Chip>
              )}
              {progress.failed > 0 && (
                <Chip size="sm" color="danger" variant="flat">
                  {progress.failed} failed
                </Chip>
              )}
              {progress.running > 0 && (
                <Chip size="sm" color="primary" variant="flat">
                  {progress.running} running
                </Chip>
              )}
            </div>
          </>
        ) : (
          <p className="text-sm text-foreground-500">
            {hasSelectedScenarios
              ? `${selectedForRun.length} scenario${selectedForRun.length !== 1 ? "s" : ""} selected`
              : hasScenarios
                ? `${runnableScenarios.length} scenarios available`
                : "No scenarios loaded"}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        {isExecuting ? (
          <Button
            color="danger"
            variant="flat"
            onPress={handleStop}
            startContent={<Icon icon="heroicons:stop" />}
          >
            Stop All
          </Button>
        ) : (
          <>
            {hasSelectedScenarios && (
              <Button
                color="primary"
                onPress={handleRunSelected}
                startContent={<Icon icon="heroicons:play" />}
              >
                Run Selected ({selectedForRun.length})
              </Button>
            )}
            <Button
              color={hasSelectedScenarios ? "default" : "primary"}
              variant={hasSelectedScenarios ? "flat" : "solid"}
              onPress={handleRunAll}
              isDisabled={!hasScenarios}
              startContent={<Icon icon="heroicons:play" />}
            >
              Run All
            </Button>
            <SimulationSettingsPopover />
          </>
        )}

        {hasExecutions && !isExecuting && (
          <Button
            variant="light"
            onPress={handleClear}
            startContent={<Icon icon="heroicons:trash" />}
          >
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
