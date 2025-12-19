import { useEffect, useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router";
import { Button, Listbox, ListboxItem, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../../stores/EvalStoreContext";
import { isPersonaScenario } from "../../../stores/evalStore";
import { RunsTable } from "./RunsTable";
import type { SimulationRun } from "../../../types";

export function RunsTab() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
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

    const runnableScenarios = config.available_scenarios.filter(
      (s) => !isPersonaScenario(s.num_tasks)
    );

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

  // Load simulation runs on mount
  useEffect(() => {
    async function loadRuns() {
      const { setSimulationRunsLoading, setSimulationRuns } =
        storeApi.getState().actions;
      setSimulationRunsLoading(true);
      try {
        const response = await client.makeRequest(
          "/api/eval/runs" as "/api/config",
        );
        // Handle response with runs property and transform snake_case to camelCase
        const rawRuns = (response as { runs?: unknown[] })?.runs ?? [];
        const runsData: SimulationRun[] = rawRuns.map((run: any) => ({
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
        setSimulationRuns(runsData);
      } catch (error) {
        console.error("Failed to load simulation runs:", error);
        setSimulationRuns([]);
      }
    }

    loadRuns();
  }, [client, storeApi]);

  const handleViewDetails = useCallback(
    (runId: string) => {
      navigate(`/runs/${runId}`);
    },
    [navigate],
  );

  const handleRerun = useCallback(
    (runId: string) => {
      // Find the run and get its scenario names
      const run = simulationRuns.find((r) => r.id === runId);
      if (run) {
        const scenarioNames = run.scenarioRuns
          .map((sr) => sr.scenarioName)
          .join(",");
        navigate(`/new?scenarios=${encodeURIComponent(scenarioNames)}`);
      }
    },
    [navigate, simulationRuns],
  );

  const handleNewRun = useCallback(() => {
    navigate("/new");
  }, [navigate]);

  const handleScenarioFilterChange = useCallback(
    (keys: "all" | Set<string>) => {
      if (keys === "all") {
        setSelectedScenarios(new Set(["all"]));
      } else {
        const newKeys = new Set(keys);
        if (newKeys.has("all") && newKeys.size > 1) {
          newKeys.delete("all");
        }
        if (newKeys.size === 0) {
          newKeys.add("all");
        }
        setSelectedScenarios(newKeys);
      }
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
          Scenarios
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
