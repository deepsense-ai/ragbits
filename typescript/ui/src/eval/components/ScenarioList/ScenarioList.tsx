import { useEffect, useRef, useCallback, useMemo } from "react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { isPersonaScenario } from "../../stores/evalStore";
import { ScenarioCard } from "./ScenarioCard";
import { Spinner, Checkbox, Chip } from "@heroui/react";
import type { Scenario, ScenarioSummary } from "../../types";

interface ScenarioGroup {
  name: string | null;
  scenarios: ScenarioSummary[];
}

export function ScenarioList() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const config = useEvalStore((s) => s.config);
  const scenarios = useEvalStore((s) => s.scenarios);
  const selectedScenarioName = useEvalStore((s) => s.selectedScenarioName);
  const selectedForRun = useEvalStore((s) => s.selectedForRun);
  const executions = useEvalStore((s) => s.executions);
  const activePersona = useEvalStore((s) => s.simulationConfig.persona);
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

  const handleViewDetails = useCallback((name: string) => {
    storeApi.getState().actions.navigateToScenarioDetail(name);
  }, [storeApi]);

  const handleRunScenario = useCallback((name: string) => {
    storeApi.getState().actions.navigateToRunner(name);
  }, [storeApi]);

  const handleTogglePersona = useCallback((name: string) => {
    const currentPersona = storeApi.getState().simulationConfig.persona;
    // Toggle: if already active, deactivate; otherwise activate
    const newPersona = currentPersona === name ? null : name;
    storeApi.getState().actions.setSimulationConfig({ persona: newPersona });
  }, [storeApi]);

  const handleSelectGroup = useCallback(
    (_groupName: string | null, groupScenarioNames: string[]) => {
      const allSelected = groupScenarioNames.every((name) =>
        selectedForRun.includes(name)
      );

      if (allSelected) {
        storeApi.getState().actions.deselectScenariosForRun(groupScenarioNames);
      } else {
        storeApi.getState().actions.selectScenariosForRun(groupScenarioNames);
      }
    },
    [storeApi, selectedForRun]
  );

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

  // Split scenarios into runnable and personas, grouped
  const { runnableGroups, personaScenarios, runnableScenarios } = useMemo(() => {
    if (!config) return { runnableGroups: [], personaScenarios: [], runnableScenarios: [] };

    const runnable = config.available_scenarios.filter(
      (s) => !isPersonaScenario(s.num_tasks)
    );
    const personas = config.available_scenarios
      .filter((s) => isPersonaScenario(s.num_tasks))
      .map((s) => s.name);

    // Group runnable scenarios by their group field
    const groupMap = new Map<string | null, ScenarioSummary[]>();
    for (const scenario of runnable) {
      const group = scenario.group;
      if (!groupMap.has(group)) {
        groupMap.set(group, []);
      }
      groupMap.get(group)!.push(scenario);
    }

    // Convert to array, with named groups first, then ungrouped
    const groups: ScenarioGroup[] = [];
    const sortedKeys = Array.from(groupMap.keys()).sort((a, b) => {
      if (a === null) return 1;
      if (b === null) return -1;
      return a.localeCompare(b);
    });

    for (const key of sortedKeys) {
      groups.push({
        name: key,
        scenarios: groupMap.get(key)!,
      });
    }

    return {
      runnableGroups: groups,
      personaScenarios: personas,
      runnableScenarios: runnable.map((s) => s.name),
    };
  }, [config]);

  const isGroupSelected = useCallback(
    (groupScenarioNames: string[]): boolean => {
      if (groupScenarioNames.length === 0) return false;
      return groupScenarioNames.every((name) => selectedForRun.includes(name));
    },
    [selectedForRun]
  );

  const isGroupPartiallySelected = useCallback(
    (groupScenarioNames: string[]): boolean => {
      if (groupScenarioNames.length === 0) return false;
      const selectedCount = groupScenarioNames.filter((name) =>
        selectedForRun.includes(name)
      ).length;
      return selectedCount > 0 && selectedCount < groupScenarioNames.length;
    },
    [selectedForRun]
  );

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

  if (runnableScenarios.length === 0 && personaScenarios.length === 0) {
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

          {/* Grouped scenarios */}
          {runnableGroups.map((group) => {
            const groupScenarioNames = group.scenarios.map((s) => s.name);
            return (
              <div key={group.name ?? "__ungrouped__"} className="mb-3">
                {/* Group header */}
                {group.name !== null ? (
                  <div className="flex items-center justify-between mb-2 px-1">
                    <div className="flex items-center gap-2">
                      <Chip size="sm" variant="flat" color="secondary">
                        {group.name}
                      </Chip>
                      <span className="text-xs text-foreground-400">
                        {group.scenarios.length}
                      </span>
                    </div>
                    <Checkbox
                      size="sm"
                      isSelected={isGroupSelected(groupScenarioNames)}
                      isIndeterminate={isGroupPartiallySelected(groupScenarioNames)}
                      onValueChange={() =>
                        handleSelectGroup(group.name, groupScenarioNames)
                      }
                    />
                  </div>
                ) : runnableGroups.length > 1 ? (
                  <div className="flex items-center justify-between mb-2 px-1">
                    <span className="text-xs text-foreground-400 uppercase tracking-wide">
                      Ungrouped
                    </span>
                    <Checkbox
                      size="sm"
                      isSelected={isGroupSelected(groupScenarioNames)}
                      isIndeterminate={isGroupPartiallySelected(groupScenarioNames)}
                      onValueChange={() =>
                        handleSelectGroup(null, groupScenarioNames)
                      }
                    />
                  </div>
                ) : null}

                {/* Scenarios in group */}
                <div className="space-y-2">
                  {group.scenarios.map((scenarioSummary) => {
                    const name = scenarioSummary.name;
                    return (
                      <ScenarioCard
                        key={name}
                        name={name}
                        scenario={scenarios[name]}
                        execution={executions[name]}
                        isSelected={selectedScenarioName === name}
                        isSelectedForRun={selectedForRun.includes(name)}
                        onSelect={() => handleSelectScenario(name)}
                        onToggleForRun={() => handleToggleForRun(name)}
                        onViewDetails={() => handleViewDetails(name)}
                        onRun={() => handleRunScenario(name)}
                        isRunnable
                      />
                    );
                  })}
                </div>
              </div>
            );
          })}
        </>
      )}

      {/* Personas Section */}
      {personaScenarios.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-foreground-500 uppercase tracking-wide mt-4 mb-2">
            Personas ({personaScenarios.length})
          </h2>
          <p className="text-xs text-foreground-400 mb-2">
            Click to activate a persona for simulation runs
          </p>
          {personaScenarios.map((name) => (
            <ScenarioCard
              key={name}
              name={name}
              scenario={scenarios[name]}
              execution={executions[name]}
              isSelected={selectedScenarioName === name}
              isSelectedForRun={false}
              onSelect={() => handleSelectScenario(name)}
              isRunnable={false}
              isPersona
              isActivePersona={activePersona === name}
              onTogglePersona={() => handleTogglePersona(name)}
            />
          ))}
        </>
      )}
    </div>
  );
}
