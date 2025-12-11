import { useEffect, useRef, useCallback, useMemo } from "react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { isPersonalityScenario } from "../../stores/evalStore";
import { ScenarioCard } from "./ScenarioCard";
import { Spinner, Checkbox } from "@heroui/react";
import type { Scenario } from "../../types";

export function ScenarioList() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const config = useEvalStore((s) => s.config);
  const scenarios = useEvalStore((s) => s.scenarios);
  const selectedScenarioName = useEvalStore((s) => s.selectedScenarioName);
  const selectedForRun = useEvalStore((s) => s.selectedForRun);
  const executions = useEvalStore((s) => s.executions);
  const loadedRef = useRef(false);

  const handleSelectScenario = useCallback((name: string) => {
    storeApi.getState().actions.selectScenario(name);
  }, [storeApi]);

  const handleToggleForRun = useCallback((name: string) => {
    storeApi.getState().actions.toggleScenarioForRun(name);
  }, [storeApi]);

  const handleSelectAll = useCallback(() => {
    storeApi.getState().actions.selectAllScenariosForRun();
  }, [storeApi]);

  const handleClearSelection = useCallback(() => {
    storeApi.getState().actions.clearScenariosForRun();
  }, [storeApi]);

  // Load scenario details when config is available
  useEffect(() => {
    if (!config || loadedRef.current) return;
    loadedRef.current = true;

    async function loadScenarios() {
      const { setScenario } = storeApi.getState().actions;
      for (const summary of config!.available_scenarios) {
        try {
          const response = await client.makeRequest(
            `/api/eval/scenarios/${summary.name}` as "/api/config",
          );
          setScenario(summary.name, response as unknown as Scenario);
        } catch (error) {
          console.error(`Failed to load scenario ${summary.name}:`, error);
        }
      }
    }

    loadScenarios();
  }, [client, config, storeApi]);

  // Split scenarios into runnable and personalities
  const { runnableScenarios, personalityScenarios } = useMemo(() => {
    if (!config) return { runnableScenarios: [], personalityScenarios: [] };
    const names = config.available_scenarios.map((s) => s.name);
    return {
      runnableScenarios: names.filter((name) => !isPersonalityScenario(name)),
      personalityScenarios: names.filter((name) => isPersonalityScenario(name)),
    };
  }, [config]);

  const allSelected = runnableScenarios.length > 0 &&
    runnableScenarios.every((name) => selectedForRun.includes(name));
  const someSelected = selectedForRun.length > 0 && !allSelected;

  if (!config) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="sm" />
      </div>
    );
  }

  if (runnableScenarios.length === 0 && personalityScenarios.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <div className="text-4xl mb-4">📭</div>
        <p className="text-foreground-500">No scenarios found</p>
        <p className="text-xs text-foreground-400 mt-2">
          Add scenario JSON files to the scenarios directory
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 p-4">
      {/* Runnable Scenarios Section */}
      {runnableScenarios.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-foreground-500 uppercase tracking-wide">
              Scenarios ({runnableScenarios.length})
            </h2>
            <div className="flex items-center gap-2">
              <Checkbox
                size="sm"
                isSelected={allSelected}
                isIndeterminate={someSelected}
                onValueChange={() => {
                  if (allSelected) {
                    handleClearSelection();
                  } else {
                    handleSelectAll();
                  }
                }}
              >
                <span className="text-xs">All</span>
              </Checkbox>
            </div>
          </div>
          {runnableScenarios.map((name) => (
            <ScenarioCard
              key={name}
              name={name}
              scenario={scenarios[name]}
              execution={executions[name]}
              isSelected={selectedScenarioName === name}
              isSelectedForRun={selectedForRun.includes(name)}
              onSelect={() => handleSelectScenario(name)}
              onToggleForRun={() => handleToggleForRun(name)}
              isRunnable
            />
          ))}
        </>
      )}

      {/* Personalities Section */}
      {personalityScenarios.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-foreground-500 uppercase tracking-wide mt-4 mb-2">
            Personalities ({personalityScenarios.length})
          </h2>
          <p className="text-xs text-foreground-400 mb-2">
            Used as simulated user profiles during scenario runs
          </p>
          {personalityScenarios.map((name) => (
            <ScenarioCard
              key={name}
              name={name}
              scenario={scenarios[name]}
              execution={executions[name]}
              isSelected={selectedScenarioName === name}
              isSelectedForRun={false}
              onSelect={() => handleSelectScenario(name)}
              isRunnable={false}
            />
          ))}
        </>
      )}
    </div>
  );
}
