import { useMemo, useCallback } from "react";
import { Checkbox, Spinner, Chip } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { isPersonaScenario } from "../../stores/evalStore";
import type { ScenarioSummary } from "../../types";

interface ScenarioGroup {
  name: string | null;
  scenarios: ScenarioSummary[];
}

export function ScenarioSelector() {
  const storeApi = useEvalStoreApi();
  const config = useEvalStore((s) => s.config);
  const scenarios = useEvalStore((s) => s.scenarios);
  const selectedForRun = useEvalStore((s) => s.selectedForRun);

  // Get runnable scenarios grouped by their group field
  const { runnableScenarios, groupedScenarios } = useMemo(() => {
    if (!config) return { runnableScenarios: [], groupedScenarios: [] };

    const runnable = config.available_scenarios.filter(
      (s) => !isPersonaScenario(s.num_tasks)
    );

    // Group scenarios by their group field
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
      runnableScenarios: runnable.map((s) => s.name),
      groupedScenarios: groups,
    };
  }, [config]);

  const handleToggle = useCallback(
    (name: string) => {
      storeApi.getState().actions.toggleScenarioForRun(name);
    },
    [storeApi]
  );

  const handleSelectAll = useCallback(() => {
    storeApi.getState().actions.selectAllScenariosForRun();
  }, [storeApi]);

  const handleClearAll = useCallback(() => {
    storeApi.getState().actions.clearScenariosForRun();
  }, [storeApi]);

  const handleSelectGroup = useCallback(
    (groupName: string | null) => {
      const group = groupedScenarios.find((g) => g.name === groupName);
      if (!group) return;

      const groupScenarioNames = group.scenarios.map((s) => s.name);
      const allSelected = groupScenarioNames.every((name) =>
        selectedForRun.includes(name)
      );

      if (allSelected) {
        storeApi.getState().actions.deselectScenariosForRun(groupScenarioNames);
      } else {
        storeApi.getState().actions.selectScenariosForRun(groupScenarioNames);
      }
    },
    [storeApi, groupedScenarios, selectedForRun]
  );

  const isGroupSelected = useCallback(
    (groupName: string | null): boolean => {
      const group = groupedScenarios.find((g) => g.name === groupName);
      if (!group || group.scenarios.length === 0) return false;
      return group.scenarios.every((s) => selectedForRun.includes(s.name));
    },
    [groupedScenarios, selectedForRun]
  );

  const isGroupPartiallySelected = useCallback(
    (groupName: string | null): boolean => {
      const group = groupedScenarios.find((g) => g.name === groupName);
      if (!group || group.scenarios.length === 0) return false;
      const selectedCount = group.scenarios.filter((s) =>
        selectedForRun.includes(s.name)
      ).length;
      return selectedCount > 0 && selectedCount < group.scenarios.length;
    },
    [groupedScenarios, selectedForRun]
  );

  const allSelected =
    runnableScenarios.length > 0 &&
    runnableScenarios.every((name) => selectedForRun.includes(name));
  const someSelected = selectedForRun.length > 0 && !allSelected;

  if (!config) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="sm" />
      </div>
    );
  }

  if (runnableScenarios.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Icon
          icon="heroicons:document-magnifying-glass"
          className="text-4xl text-foreground-300 mb-3"
        />
        <p className="text-foreground-500 text-sm">No scenarios available</p>
        <p className="text-xs text-foreground-400 mt-1">
          Add scenario JSON files to the scenarios directory
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header with select all */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-divider">
        <span className="text-xs text-foreground-500">
          {selectedForRun.length} of {runnableScenarios.length} selected
        </span>
        <Checkbox
          size="sm"
          isSelected={allSelected}
          isIndeterminate={someSelected}
          onValueChange={() => {
            if (allSelected) {
              handleClearAll();
            } else {
              handleSelectAll();
            }
          }}
        >
          <span className="text-xs">All</span>
        </Checkbox>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {groupedScenarios.map((group) => (
          <div key={group.name ?? "__ungrouped__"}>
            {/* Group header */}
            {group.name !== null ? (
              <div className="flex items-center justify-between mb-2">
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
                  isSelected={isGroupSelected(group.name)}
                  isIndeterminate={isGroupPartiallySelected(group.name)}
                  onValueChange={() => handleSelectGroup(group.name)}
                >
                  <span className="text-xs">All</span>
                </Checkbox>
              </div>
            ) : groupedScenarios.length > 1 ? (
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-foreground-400 uppercase tracking-wide">
                  Ungrouped
                </span>
                <Checkbox
                  size="sm"
                  isSelected={isGroupSelected(null)}
                  isIndeterminate={isGroupPartiallySelected(null)}
                  onValueChange={() => handleSelectGroup(null)}
                >
                  <span className="text-xs">All</span>
                </Checkbox>
              </div>
            ) : null}

            {/* Scenarios in group - grid layout, 3 per row */}
            <div className="grid grid-cols-3 gap-2">
              {group.scenarios.map((scenarioSummary) => {
                const name = scenarioSummary.name;
                const scenario = scenarios[name];
                const isSelected = selectedForRun.includes(name);
                const taskCount =
                  scenario?.tasks.length ?? scenarioSummary.num_tasks;

                return (
                  <button
                    key={name}
                    onClick={() => handleToggle(name)}
                    className={`
                      flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors
                      ${
                        isSelected
                          ? "bg-primary-100 dark:bg-primary-900/30 border-primary-300 dark:border-primary-700"
                          : "bg-content2 border-transparent hover:bg-content3"
                      }
                    `}
                  >
                    <Checkbox
                      size="sm"
                      isSelected={isSelected}
                      onValueChange={() => handleToggle(name)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-sm font-medium truncate">{name}</p>
                      <p className="text-xs text-foreground-500">
                        {taskCount} task{taskCount !== 1 ? "s" : ""}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
