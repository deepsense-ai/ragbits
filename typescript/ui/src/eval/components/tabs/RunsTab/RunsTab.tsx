import { useEffect, useState, useMemo, useCallback } from "react";
import { useLocation, useNavigate } from "react-router";
import { Button, Listbox, ListboxItem, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../../stores/EvalStoreContext";
import { RunsTable } from "./RunsTable";
import type { SimulationRun } from "../../../types";

export function RunsTab() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const location = useLocation();
  const navigate = useNavigate();

  const config = useEvalStore((s) => s.config);
  const simulationRunsFromStore = useEvalStore((s) => s.simulationRuns);
  const isLoading = useEvalStore((s) => s.isSimulationRunsLoading);

  // Ensure simulationRuns is always an array
  const simulationRuns = Array.isArray(simulationRunsFromStore)
    ? simulationRunsFromStore
    : [];

  const [selectedScenarios, setSelectedScenarios] = useState<Set<string>>(
    new Set(["all"]),
  );

  // Get runnable scenarios (non-personas) and build group mappings
  const { scenarios, groupScenarios } = useMemo(() => {
    if (!config) {
      return {
        scenarios: [],
        groupScenarios: new Map<string, string[]>(),
      };
    }

    const runnableScenarios = config.available_scenarios;

    // Build group -> scenarios mapping
    const groupToScenarios = new Map<string, string[]>();
    for (const s of runnableScenarios) {
      if (s.group) {
        if (!groupToScenarios.has(s.group)) {
          groupToScenarios.set(s.group, []);
        }
        groupToScenarios.get(s.group)!.push(s.name);
      }
    }

    return {
      scenarios: runnableScenarios.map((s) => s.name),
      groupScenarios: groupToScenarios,
    };
  }, [config]);

  // Filter simulation runs by selected scenarios
  const filteredRuns = useMemo(() => {
    if (selectedScenarios.has("all")) {
      return simulationRuns;
    }
    // Filter runs that contain at least one of the selected scenarios
    return simulationRuns.filter((run) =>
      run.scenarioRuns.some((sr) => selectedScenarios.has(sr.scenarioName)),
    );
  }, [simulationRuns, selectedScenarios]);

  // Load simulation runs each time the tab is shown, merging with in-progress runs
  useEffect(() => {
    async function loadRuns() {
      const { setSimulationRunsLoading, setSimulationRuns } =
        storeApi.getState().actions;
      const existingRuns = storeApi.getState().simulationRuns ?? [];
      setSimulationRunsLoading(true);
      try {
        const response = await client.makeRequest(
          "/api/eval/runs" as "/api/config",
        );
        // Handle response with runs property and transform snake_case to camelCase
        const rawRuns = (response as { runs?: unknown[] })?.runs ?? [];
        const apiRuns: SimulationRun[] = rawRuns.map((run: any) => ({
          id: run.id,
          timestamp: run.timestamp,
          version: run.version || "current",
          status: run.status,
          scenarioRuns: (run.scenario_runs || []).map((sr: any) => ({
            id: sr.id,
            scenarioName: sr.scenario_name,
            persona: sr.persona || null,
            status: sr.status,
            startTime: sr.start_time,
            endTime: sr.end_time,
            turns: [],
            tasks: [],
            responseChunks: [],
            metrics: {
              total_turns: sr.total_turns || 0,
              total_tasks: sr.total_tasks || 0,
              tasks_completed: sr.tasks_completed || 0,
              success_rate: sr.success_rate || 0,
              total_tokens: sr.total_tokens || 0,
              prompt_tokens: 0,
              completion_tokens: 0,
              total_cost_usd: sr.total_cost_usd || 0,
              deepeval_scores: {},
              custom: {},
            },
            error: sr.error,
          })),
          config: {
            max_turns_scenario: 15,
            max_turns_task: 4,
            sim_user_model_name: null,
            checker_model_name: null,
            default_model: "gpt-4o-mini",
            persona: null,
          },
          group: run.group || null,
          totalScenarios: run.total_scenarios || 0,
          completedScenarios: run.completed_scenarios || 0,
          failedScenarios: run.failed_scenarios || 0,
          totalTokens: run.total_tokens || 0,
          totalCostUsd: run.total_cost_usd || 0,
          overallSuccessRate: run.overall_success_rate || 0,
        }));
        // Merge: prefer store version for runs in both (store has live SSE data
        // + allDone-merged API data, and accurate scenario counts from the start).
        // Only use API data for runs NOT in the store (historical runs from prior sessions).
        const storeRunIds = new Set(existingRuns.map((r) => r.id));
        const apiOnlyRuns = apiRuns.filter((r) => !storeRunIds.has(r.id));
        // Preserve existing store runs order but ensure API-only (older) runs come after
        setSimulationRuns([...existingRuns, ...apiOnlyRuns]);
      } catch (error) {
        console.error("Failed to load simulation runs:", error);
      }
    }

    loadRuns();
  }, [client, storeApi, location.pathname]);

  const handleViewDetails = useCallback(
    (runIdWithParams: string) => {
      navigate(`/runs/${runIdWithParams}`);
    },
    [navigate],
  );

  const handleRerun = useCallback(
    async (runId: string) => {
      const run = simulationRuns.find((r) => r.id === runId);
      if (!run) return;
      try {
        const { rerunSimulation } = await import("../../../utils/rerunSimulation");
        const newRunId = await rerunSimulation(run, client, storeApi as any);
        navigate(`/runs/${newRunId}`);
      } catch (err) {
        console.error("Rerun failed:", err);
      }
    },
    [client, storeApi, navigate, simulationRuns],
  );

  const handleNewRun = useCallback(() => {
    navigate("/new");
  }, [navigate]);

  const handleScenarioFilterChange = useCallback(
    (keys: "all" | Set<string>) => {
      if (keys === "all") {
        setSelectedScenarios(new Set(["all"]));
        return;
      }
      const newKeys = new Set(keys);
      setSelectedScenarios((prev) => {
        const allWasSelected = prev.has("all");
        const allNowSelected = newKeys.has("all");

        // User just clicked "All Scenarios" — deselect everything else
        if (allNowSelected && !allWasSelected) {
          return new Set(["all"]);
        }
        // User selected an individual scenario while "all" was active — drop "all"
        if (allNowSelected && allWasSelected && newKeys.size > 1) {
          newKeys.delete("all");
        }
        // Nothing selected — fall back to "all"
        if (newKeys.size === 0) {
          newKeys.add("all");
        }
        return newKeys;
      });
    },
    [],
  );

  if (!config) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left Sidebar - Scenario Filter */}
      <aside className="w-56 flex-shrink-0 border-r border-divider p-4">
        <h2 className="mb-3 text-sm font-semibold text-foreground-500 uppercase tracking-wide">
          Scenario filter
        </h2>
        <Listbox
          aria-label="Filter by scenario"
          selectionMode="multiple"
          selectedKeys={selectedScenarios}
          onSelectionChange={
            handleScenarioFilterChange as (keys: "all" | Set<React.Key>) => void
          }
          items={[
            { key: "all", label: "All Scenarios" },
            ...scenarios.map((name) => ({ key: name, label: name })),
          ]}
          classNames={{
            list: "gap-1",
          }}
        >
          {(item) => (
            <ListboxItem key={item.key} className="text-sm">
              {item.label}
            </ListboxItem>
          )}
        </Listbox>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-divider px-6 py-4">
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              Simulation Runs
            </h2>
            <p className="text-sm text-foreground-500">
              {filteredRuns.length} run{filteredRuns.length !== 1 ? "s" : ""}{" "}
              {!selectedScenarios.has("all") && `(filtered)`}
            </p>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex h-full items-center justify-center">
              <Spinner size="lg" />
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <Icon
                icon="heroicons:inbox"
                className="text-6xl text-foreground-300 mb-4"
              />
              <p className="text-foreground-500">No runs found</p>
              <p className="text-sm text-foreground-400 mt-1">
                Start a new run to see results here
              </p>
            </div>
          ) : (
            <RunsTable
              runs={filteredRuns}
              groupScenarios={groupScenarios}
              onViewDetails={handleViewDetails}
              onRerun={handleRerun}
            />
          )}
        </div>

        {/* Footer with New Run button */}
        <div className="flex justify-end border-t border-divider px-6 py-4">
          <Button
            color="success"
            onPress={handleNewRun}
            startContent={<Icon icon="heroicons:sparkles" />}
          >
            New run
          </Button>
        </div>
      </div>
    </div>
  );
}
