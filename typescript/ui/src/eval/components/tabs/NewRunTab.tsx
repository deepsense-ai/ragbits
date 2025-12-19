import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { ScenarioSelector } from "../NewRun/ScenarioSelector";
import { RunConfigForm } from "../NewRun/RunConfigForm";
import type { ProgressUpdate, SimulationRun } from "../../types";
import { selectProgress } from "../../stores/evalStore";

export function NewRunTab() {
  const navigate = useNavigate();
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const selectedForRun = useEvalStore((s) => s.selectedForRun);
  const selectedPersonas = useEvalStore((s) => s.selectedPersonas);
  const isExecuting = useEvalStore((s) => s.isExecuting);

  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Helper to detect if all selected scenarios belong to the same group
  const detectRunGroup = useCallback((): string | null => {
    const config = storeApi.getState().config;
    const currentSelectedForRun = storeApi.getState().selectedForRun;
    if (!config || currentSelectedForRun.length === 0) return null;

    const selectedScenarios = config.available_scenarios.filter((s) =>
      currentSelectedForRun.includes(s.name)
    );

    // Check if all selected scenarios have the same non-null group
    const groups = new Set(selectedScenarios.map((s) => s.group));
    if (groups.size === 1) {
      const group = selectedScenarios[0]?.group;
      return group ?? null;
    }
    return null;
  }, [storeApi]);

  const handleStartRun = useCallback(async () => {
    const currentSelectedForRun = storeApi.getState().selectedForRun;
    const currentSelectedPersonas = storeApi.getState().selectedPersonas;
    const currentSimulationConfig = storeApi.getState().simulationConfig;

    if (currentSelectedForRun.length === 0) return;

    // Detect if all scenarios belong to the same group
    const runGroup = detectRunGroup();

    setIsStarting(true);
    setError(null);

    try {
      // Start the evaluation run - single request with scenarios and personas
      const response = await fetch(`${client.getBaseUrl()}/api/eval/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario_names: currentSelectedForRun,
          personas: currentSelectedPersonas.length > 0 ? currentSelectedPersonas : null,
          config: currentSimulationConfig,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start evaluation: ${response.statusText}`);
      }

      const data = await response.json();
      const runId = data.run_id;
      if (!runId) {
        throw new Error("Invalid response: missing run_id");
      }

      // Determine personas for creating scenario runs matrix
      const personasForMatrix: (string | null)[] = currentSelectedPersonas.length > 0
        ? currentSelectedPersonas
        : [null];

      // Create initial SimulationRun entry with scenario × persona matrix
      const scenarioRuns = [];
      for (const scenarioName of currentSelectedForRun) {
        for (const persona of personasForMatrix) {
          scenarioRuns.push({
            id: `${runId}_${scenarioName}${persona ? `:${persona}` : ""}`,
            scenarioName,
            persona,
            status: "queued" as const,
            startTime: new Date().toISOString(),
            endTime: null,
            turns: [],
            tasks: [],
            metrics: null,
            error: null,
          });
        }
      }

      const initialRun: SimulationRun = {
        id: runId,
        timestamp: new Date().toISOString(),
        version: "current",
        status: "running",
        config: currentSimulationConfig,
        group: runGroup,
        scenarioRuns,
        totalScenarios: scenarioRuns.length,
        completedScenarios: 0,
        failedScenarios: 0,
        totalTokens: 0,
        totalCostUsd: 0,
        overallSuccessRate: 0,
      };
      storeApi.getState().actions.addSimulationRun(initialRun);

      // Initialize execution state
      storeApi.getState().actions.startExecution(runId, currentSelectedForRun);

      // Connect to SSE stream for progress updates
      const eventSource = new EventSource(
        `${client.getBaseUrl()}/api/eval/progress/${runId}`
      );

      eventSource.onmessage = (event) => {
        try {
          const update: ProgressUpdate = JSON.parse(event.data);
          storeApi.getState().actions.handleProgressUpdate(update);

          // Update the SimulationRun based on progress
          const currentRun = storeApi.getState().simulationRuns.find((r) => r.id === runId);
          if (currentRun) {
            // Find scenario run - first try by scenario_run_id (after it's been synced)
            // If not found, fall back to scenario_name + persona for initial matching
            let scenarioIndex = currentRun.scenarioRuns.findIndex(
              (sr) => sr.id === update.scenario_run_id
            );
            if (scenarioIndex === -1) {
              // Fall back to scenario_name + persona matching for first update
              // Find the first unsynced scenario run with matching name/persona
              scenarioIndex = currentRun.scenarioRuns.findIndex(
                (sr) => sr.scenarioName === update.scenario_name &&
                        (sr.persona ?? null) === (update.persona ?? null) &&
                        !sr.id.startsWith("sr_")  // Not yet synced with backend ID
              );
            }
            if (scenarioIndex !== -1) {
              const updatedScenarioRuns = [...currentRun.scenarioRuns];
              const scenarioRun = { ...updatedScenarioRuns[scenarioIndex] };

              // Sync the ID with the backend-generated scenario_run_id
              if (update.scenario_run_id && scenarioRun.id !== update.scenario_run_id) {
                scenarioRun.id = update.scenario_run_id;
              }

              if (update.type === "status") {
                scenarioRun.status = update.status;
              } else if (update.type === "turn") {
                scenarioRun.status = "running";
                scenarioRun.turns = [
                  ...scenarioRun.turns,
                  {
                    turn_index: update.turn_index,
                    task_index: update.task_index,
                    user_message: update.user_message,
                    assistant_message: update.assistant_message,
                    tool_calls: update.tool_calls,
                    task_completed: update.task_completed,
                    task_completed_reason: update.task_completed_reason,
                    token_usage: null,
                    latency_ms: null,
                    checkers: update.checkers,
                    checker_mode: update.checker_mode,
                  },
                ];
              } else if (update.type === "response_chunk") {
                if (!scenarioRun.responseChunks) {
                  scenarioRun.responseChunks = [];
                }
                scenarioRun.responseChunks = [
                  ...scenarioRun.responseChunks,
                  {
                    turn_index: update.turn_index,
                    task_index: update.task_index,
                    chunk_index: scenarioRun.responseChunks.length,
                    chunk_type: update.chunk_type,
                    chunk_data: update.chunk_data,
                    timestamp: Date.now(),
                  },
                ];
              } else if (update.type === "complete") {
                scenarioRun.status = update.status;
                scenarioRun.endTime = new Date().toISOString();
              } else if (update.type === "error") {
                scenarioRun.status = "failed";
                scenarioRun.error = update.error;
                scenarioRun.endTime = new Date().toISOString();
              }

              updatedScenarioRuns[scenarioIndex] = scenarioRun;

              const completed = updatedScenarioRuns.filter((sr) => sr.status === "completed").length;
              const failed = updatedScenarioRuns.filter((sr) => sr.status === "failed" || sr.status === "timeout").length;
              const allDone = completed + failed === updatedScenarioRuns.length;

              storeApi.getState().actions.updateSimulationRun(runId, {
                scenarioRuns: updatedScenarioRuns,
                status: allDone ? (failed > 0 ? "failed" : "completed") : "running",
                completedScenarios: completed,
                failedScenarios: failed,
              });
            }
          }

          if (update.type === "complete" || update.type === "error") {
            const currentProgress = selectProgress(storeApi.getState());
            if (currentProgress.running === 0) {
              eventSource.close();
            }
          }
        } catch (err) {
          console.error("Failed to parse progress update:", err);
        }
      };

      eventSource.onerror = () => {
        console.error("SSE connection error");
        eventSource.close();
      };

      // Clear selection and navigate to run detail page
      storeApi.getState().actions.clearScenariosForRun();
      storeApi.getState().actions.clearPersonasForRun();
      navigate(`/runs/${runId}`);
    } catch (err) {
      console.error("Failed to start evaluation:", err);
      setError(err instanceof Error ? err.message : "Failed to start run");
      setIsStarting(false);
    }
  }, [client, storeApi, navigate, detectRunGroup]);

  // Calculate total runs (scenarios × personas matrix)
  const totalRuns = selectedForRun.length * Math.max(selectedPersonas.length, 1);
  const canStart = selectedForRun.length > 0 && !isExecuting && !isStarting;

  return (
    <div className="flex h-full">
      {/* Left column - Scenario selection (50% width) */}
      <div className="w-1/2 border-r border-divider flex flex-col">
        {/* Header aligned with right side */}
        <div className="px-4 py-3 border-b border-divider">
          <h2 className="text-lg font-semibold">Select Scenarios</h2>
          <p className="text-sm text-foreground-500 mt-0.5">
            Choose scenarios to run
          </p>
        </div>
        <ScenarioSelector />
      </div>

      {/* Right column - Configuration */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header aligned with left side */}
        <div className="px-6 py-3 border-b border-divider">
          <h2 className="text-lg font-semibold">Configuration</h2>
          <p className="text-sm text-foreground-500 mt-0.5">
            Configure the simulation parameters
          </p>
        </div>

        {/* Config form */}
        <div className="flex-1 overflow-auto p-6">
          <RunConfigForm />
        </div>

        {/* Footer with run button */}
        <div className="px-6 py-4 border-t border-divider">
          {error && (
            <div className="mb-3 p-3 bg-danger-50 dark:bg-danger-900/20 rounded-lg">
              <p className="text-sm text-danger">{error}</p>
            </div>
          )}
          <Button
            color="primary"
            size="lg"
            className="w-full"
            isDisabled={!canStart}
            isLoading={isStarting}
            onPress={handleStartRun}
            startContent={
              !isStarting && <Icon icon="heroicons:play" className="text-lg" />
            }
          >
            {isStarting
              ? "Starting..."
              : selectedForRun.length > 0
                ? selectedPersonas.length > 1
                  ? `Start ${totalRuns} Runs (${selectedForRun.length} scenarios × ${selectedPersonas.length} personas)`
                  : `Start Run (${selectedForRun.length} scenario${selectedForRun.length !== 1 ? "s" : ""})`
                : "Select scenarios to run"}
          </Button>
        </div>
      </div>
    </div>
  );
}
