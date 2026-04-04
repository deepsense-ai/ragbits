import { useState, useEffect, useMemo, useRef } from "react";
import { Card, CardBody, Chip, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import type { Scenario, ScenarioSummary } from "../../types";

interface ScenarioGroup {
  name: string | null;
  scenarios: ScenarioSummary[];
}

export function ScenariosTab() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const config = useEvalStore((s) => s.config);
  const scenarios = useEvalStore((s) => s.scenarios);
  const loadedRef = useRef(false);

  const [selectedName, setSelectedName] = useState<string | null>(null);

  // Get runnable scenarios (not personas) grouped
  const { groupedScenarios, allScenarioNames } = useMemo(() => {
    if (!config) return { groupedScenarios: [], allScenarioNames: [] };

    const runnable = config.available_scenarios;

    // Group by group field
    const groupMap = new Map<string | null, ScenarioSummary[]>();
    for (const scenario of runnable) {
      const group = scenario.group;
      if (!groupMap.has(group)) {
        groupMap.set(group, []);
      }
      groupMap.get(group)!.push(scenario);
    }

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
      groupedScenarios: groups,
      allScenarioNames: runnable.map((s) => s.name),
    };
  }, [config]);

  // Load scenario details
  useEffect(() => {
    if (!config || loadedRef.current) return;
    loadedRef.current = true;

    async function loadScenarios() {
      const { setScenario } = storeApi.getState().actions;
      for (const summary of config!.available_scenarios) {
        try {
          const response = await client.makeRequest(
            `/api/eval/scenarios/${summary.name}` as "/api/config"
          );
          setScenario(summary.name, response as unknown as Scenario);
        } catch (error) {
          console.error(`Failed to load scenario ${summary.name}:`, error);
        }
      }
    }

    loadScenarios();
  }, [client, config, storeApi]);

  // Auto-select first scenario
  useEffect(() => {
    if (!selectedName && allScenarioNames.length > 0) {
      setSelectedName(allScenarioNames[0]);
    }
  }, [selectedName, allScenarioNames]);

  const selectedScenario = selectedName ? scenarios[selectedName] : null;
  const selectedSummary = config?.available_scenarios.find(
    (s) => s.name === selectedName
  );

  if (!config) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (allScenarioNames.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Icon
          icon="heroicons:document-magnifying-glass"
          className="text-6xl text-foreground-300 mb-4"
        />
        <h2 className="text-xl font-semibold text-foreground mb-2">
          No Scenarios Found
        </h2>
        <p className="text-foreground-500 max-w-md">
          Add scenario JSON files to the scenarios directory to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left: Scenario list */}
      <aside className="w-72 flex-shrink-0 border-r border-divider overflow-y-auto">
        <div className="p-4">
          <h3 className="text-sm font-semibold text-foreground-500 uppercase tracking-wide mb-3">
            Scenarios ({allScenarioNames.length})
          </h3>
          <div className="space-y-4">
            {groupedScenarios.map((group) => (
              <div key={group.name ?? "__ungrouped__"}>
                {group.name !== null && (
                  <div className="flex items-center gap-2 mb-2">
                    <Chip size="sm" variant="flat" color="secondary">
                      {group.name}
                    </Chip>
                    <span className="text-xs text-foreground-400">
                      {group.scenarios.length}
                    </span>
                  </div>
                )}
                <div className="space-y-1">
                  {group.scenarios.map((summary) => (
                    <Card
                      key={summary.name}
                      isPressable
                      onPress={() => setSelectedName(summary.name)}
                      className={`w-full ${
                        selectedName === summary.name
                          ? "border-2 border-primary"
                          : ""
                      }`}
                    >
                      <CardBody className="p-3">
                        <p className="font-medium truncate">{summary.name}</p>
                        <p className="text-xs text-foreground-400">
                          {summary.num_tasks} task{summary.num_tasks !== 1 ? "s" : ""}
                        </p>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* Right: Scenario detail */}
      <main className="flex-1 min-h-0 overflow-auto">
        {selectedScenario ? (
          <ScenarioDetail
            scenario={selectedScenario}
            group={selectedSummary?.group}
          />
        ) : selectedName ? (
          <div className="flex h-full items-center justify-center">
            <Spinner size="sm" />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-foreground-500">
            Select a scenario to view details
          </div>
        )}
      </main>
    </div>
  );
}

function ScenarioDetail({
  scenario,
  group,
}: {
  scenario: Scenario;
  group?: string | null;
}) {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h2 className="text-2xl font-semibold">{scenario.name}</h2>
          {group && (
            <Chip size="sm" variant="flat" color="secondary">
              {group}
            </Chip>
          )}
        </div>
        <p className="text-foreground-500">
          {scenario.tasks.length} task{scenario.tasks.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Tasks */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Tasks</h3>
        {scenario.tasks.map((task, index) => (
          <Card key={index}>
            <CardBody className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-semibold text-primary">
                    {index + 1}
                  </span>
                </div>
                <div className="flex-1">
                  <p className="text-foreground mb-3">{task.task}</p>

                  {/* Checker details - compact two-row layout */}
                  <div className="rounded-lg bg-content2 px-3 py-2.5 space-y-2">
                    {/* Expected result row */}
                    {task.checkers.some((c) => c.type === "llm" && c.expected_result) && (
                      <div className="flex items-baseline gap-2">
                        <Icon icon="heroicons:chat-bubble-left-ellipsis" className="text-secondary text-sm flex-shrink-0 mt-0.5" />
                        <p className="text-sm">
                          <span className="text-foreground-400 font-medium">Expected </span>
                          <span className="text-foreground-600 italic">
                            {String(task.checkers.find((c) => c.type === "llm")?.expected_result)}
                          </span>
                        </p>
                      </div>
                    )}

                    {/* Tools row */}
                    {task.checkers.some((c) => c.type === "tool_call" && c.tools) && (() => {
                      const toolChecker = task.checkers.find((c) => c.type === "tool_call");
                      const tools = (toolChecker?.tools as (string | { name: string })[]) ?? [];
                      return (
                        <div className="flex items-center gap-2 flex-wrap">
                          <Icon icon="heroicons:wrench-screwdriver" className="text-warning text-sm flex-shrink-0" />
                          <span className="text-sm text-foreground-400 font-medium">Tools</span>
                          {tools.map((tool, j) => (
                            <Chip key={j} size="sm" variant="flat" color="warning">
                              {typeof tool === "string" ? tool : tool.name}
                            </Chip>
                          ))}
                          {toolChecker?.mode && toolChecker.mode !== "all" && (
                            <Chip size="sm" variant="flat">
                              match: {String(toolChecker.mode)}
                            </Chip>
                          )}
                        </div>
                      );
                    })()}

                    {/* State checks row */}
                    {task.checkers.some((c) => c.type === "state" && c.checks) && (
                      <div className="flex items-baseline gap-2">
                        <Icon icon="heroicons:variable" className="text-primary text-sm flex-shrink-0 mt-0.5" />
                        <p className="text-sm">
                          <span className="text-foreground-400 font-medium">State </span>
                          <span className="text-foreground-600 italic">
                            {JSON.stringify(task.checkers.find((c) => c.type === "state")?.checks)}
                          </span>
                        </p>
                      </div>
                    )}

                  </div>
                </div>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
    </div>
  );
}
