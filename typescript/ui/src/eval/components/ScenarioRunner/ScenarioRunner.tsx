import { useCallback, useMemo, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  Chip,
  ScrollShadow,
  Divider,
  Tabs,
  Tab,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { selectProgress } from "../../stores/evalStore";
import type { ProgressUpdate, RunHistoryEntry, ScenarioExecution } from "../../types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ResponsesView } from "../ResultsView/ResponsesView";

const EMPTY_ARRAY: RunHistoryEntry[] = [];

type RunnerViewMode = "conversation" | "responses";

export function ScenarioRunner() {
  const { client } = useRagbitsContext();
  const storeApi = useEvalStoreApi();
  const selectedScenarioName = useEvalStore((s) => s.selectedScenarioName);
  const scenarios = useEvalStore((s) => s.scenarios);
  const runHistoryMap = useEvalStore((s) => s.runHistory);
  const selectedRunId = useEvalStore((s) => s.selectedRunId);
  const isExecuting = useEvalStore((s) => s.isExecuting);
  const executions = useEvalStore((s) => s.executions);
  const [viewMode, setViewMode] = useState<RunnerViewMode>("conversation");

  // Derive values from stable selectors
  const scenario = selectedScenarioName ? scenarios[selectedScenarioName] : null;
  const runHistory = selectedScenarioName ? runHistoryMap[selectedScenarioName] ?? EMPTY_ARRAY : EMPTY_ARRAY;
  const currentExecution = selectedScenarioName ? executions[selectedScenarioName] : null;

  // Get the execution to display - either from selected run history or current
  const displayExecution: ScenarioExecution | null = useMemo(() => {
    if (selectedRunId) {
      const historyEntry = runHistory.find((r) => r.runId === selectedRunId);
      return historyEntry?.execution ?? null;
    }
    return currentExecution;
  }, [selectedRunId, runHistory, currentExecution]);

  const handleBack = useCallback(() => {
    storeApi.getState().actions.navigateBack();
  }, [storeApi]);

  const handleBackToDetail = useCallback(() => {
    if (selectedScenarioName) {
      storeApi.getState().actions.navigateToScenarioDetail(selectedScenarioName);
    }
  }, [storeApi, selectedScenarioName]);

  const handleSelectRun = useCallback(
    (runId: string | null) => {
      storeApi.getState().actions.selectRun(runId);
    },
    [storeApi]
  );

  const handleRunScenario = useCallback(async () => {
    if (!selectedScenarioName || isExecuting) return;

    const currentSimulationConfig = storeApi.getState().simulationConfig;

    try {
      const response = await fetch(`${client.getBaseUrl()}/api/eval/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario_names: [selectedScenarioName],
          config: currentSimulationConfig,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start evaluation: ${response.statusText}`);
      }

      const data = await response.json();
      const runId = data.run_id;

      // Clear any selected historical run
      storeApi.getState().actions.selectRun(null);

      // Initialize execution state
      storeApi.getState().actions.startExecution(runId, [selectedScenarioName]);

      // Connect to SSE stream for progress updates
      const eventSource = new EventSource(
        `${client.getBaseUrl()}/api/eval/progress/${runId}`
      );

      eventSource.onmessage = (event) => {
        try {
          const update: ProgressUpdate = JSON.parse(event.data);
          storeApi.getState().actions.handleProgressUpdate(update);

          // When completed, add to run history
          if (update.type === "complete" || update.type === "error") {
            const execution = storeApi.getState().executions[selectedScenarioName];
            if (execution) {
              const historyEntry: RunHistoryEntry = {
                runId,
                scenarioName: selectedScenarioName,
                timestamp: Date.now(),
                status: execution.status,
                execution: { ...execution },
              };
              storeApi.getState().actions.addToRunHistory(selectedScenarioName, historyEntry);
            }

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
  }, [client, storeApi, selectedScenarioName, isExecuting]);

  const handleStop = useCallback(() => {
    storeApi.getState().actions.stopExecution();
  }, [storeApi]);

  if (!selectedScenarioName || !scenario) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-foreground-500">No scenario selected</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Run History Sidebar */}
      <aside className="w-72 flex-shrink-0 border-r border-divider flex flex-col">
        <div className="p-4 border-b border-divider">
          <h2 className="font-semibold text-foreground">Run History</h2>
          <p className="text-xs text-foreground-500 mt-1">
            {runHistory.length} previous run{runHistory.length !== 1 ? "s" : ""}
          </p>
        </div>
        <ScrollShadow className="flex-1">
          <div className="p-2 space-y-2">
            {/* Current Run Option */}
            {currentExecution && (
              <Card
                isPressable
                onPress={() => handleSelectRun(null)}
                className={!selectedRunId ? "ring-2 ring-primary" : ""}
              >
                <CardBody className="p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <StatusChip status={currentExecution.status} />
                      <span className="text-xs text-foreground-500">Current</span>
                    </div>
                    {currentExecution.status === "running" && (
                      <Icon
                        icon="heroicons:arrow-path"
                        className="animate-spin text-primary text-sm"
                      />
                    )}
                  </div>
                  <p className="text-xs text-foreground-400 mt-1">
                    {currentExecution.turns.length} turns
                  </p>
                </CardBody>
              </Card>
            )}

            {/* Historical Runs */}
            {runHistory.map((run) => (
              <Card
                key={run.runId}
                isPressable
                onPress={() => handleSelectRun(run.runId)}
                className={selectedRunId === run.runId ? "ring-2 ring-primary" : ""}
              >
                <CardBody className="p-3">
                  <div className="flex items-center justify-between">
                    <StatusChip status={run.status} />
                  </div>
                  <p className="text-xs text-foreground mt-2">
                    {new Date(run.timestamp).toLocaleString()}
                  </p>
                  <p className="text-xs text-foreground-400">
                    {run.execution.turns.length} turns
                  </p>
                </CardBody>
              </Card>
            ))}

            {runHistory.length === 0 && !currentExecution && (
              <div className="text-center py-8">
                <Icon
                  icon="heroicons:clock"
                  className="text-4xl text-foreground-300 mx-auto mb-2"
                />
                <p className="text-sm text-foreground-500">No runs yet</p>
                <p className="text-xs text-foreground-400 mt-1">
                  Run the scenario to see results
                </p>
              </div>
            )}
          </div>
        </ScrollShadow>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="border-b border-divider px-6 py-4">
          <div className="flex items-center gap-4">
            <Button
              isIconOnly
              variant="light"
              onPress={handleBack}
              aria-label="Go back to scenarios"
            >
              <Icon icon="heroicons:arrow-left" className="text-xl" />
            </Button>
            <div className="flex-1">
              <h1 className="text-xl font-semibold text-foreground">
                {scenario.name}
              </h1>
              <p className="text-sm text-foreground-500">
                {scenario.tasks.length} tasks
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="flat"
                onPress={handleBackToDetail}
                startContent={<Icon icon="heroicons:document-text" />}
              >
                View Details
              </Button>
              {isExecuting ? (
                <Button
                  color="danger"
                  variant="flat"
                  onPress={handleStop}
                  startContent={<Icon icon="heroicons:stop" />}
                >
                  Stop
                </Button>
              ) : (
                <Button
                  color="primary"
                  onPress={handleRunScenario}
                  startContent={<Icon icon="heroicons:play" />}
                >
                  Run
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* View Tabs and Content */}
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="border-b border-divider px-4 py-2">
            <Tabs
              selectedKey={viewMode}
              onSelectionChange={(key) => setViewMode(key as RunnerViewMode)}
              size="sm"
              variant="underlined"
            >
              <Tab
                key="conversation"
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="heroicons:chat-bubble-left-right" />
                    <span>Conversation</span>
                  </div>
                }
              />
              <Tab
                key="responses"
                title={
                  <div className="flex items-center gap-2">
                    <Icon icon="heroicons:squares-2x2" />
                    <span>Responses</span>
                  </div>
                }
              />
            </Tabs>
          </div>

          {/* Content */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {viewMode === "conversation" ? (
              displayExecution ? (
                <ConversationDisplay
                  execution={displayExecution}
                  scenario={scenario}
                />
              ) : (
                <div className="flex h-full flex-col items-center justify-center p-8 text-center">
                  <Icon
                    icon="heroicons:play-circle"
                    className="text-6xl text-foreground-300 mb-4"
                  />
                  <h2 className="text-lg font-medium text-foreground">
                    Ready to Run
                  </h2>
                  <p className="text-sm text-foreground-500 mt-2">
                    Click "Run" to start the scenario evaluation
                  </p>
                </div>
              )
            ) : (
              <ResponsesView scenarioName={selectedScenarioName} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const config: Record<string, { color: "success" | "danger" | "warning" | "primary" | "default"; label: string }> = {
    completed: { color: "success", label: "Completed" },
    failed: { color: "danger", label: "Failed" },
    timeout: { color: "warning", label: "Timeout" },
    running: { color: "primary", label: "Running" },
    queued: { color: "primary", label: "Queued" },
    idle: { color: "default", label: "Idle" },
  };
  const { color, label } = config[status] ?? { color: "default", label: status };
  return (
    <Chip size="sm" color={color} variant="flat">
      {label}
    </Chip>
  );
}

interface ConversationDisplayProps {
  execution: ScenarioExecution;
  scenario: { name: string; tasks: { task: string; expected_result: string }[] };
}

function ConversationDisplay({ execution, scenario }: ConversationDisplayProps) {
  if (execution.turns.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <Icon
          icon="heroicons:clock"
          className="text-6xl text-foreground-300 mb-4"
        />
        <h2 className="text-lg font-medium text-foreground">
          {execution.status === "running" || execution.status === "queued"
            ? "Starting..."
            : "No Turns"}
        </h2>
        <p className="text-sm text-foreground-500 mt-2">
          {execution.status === "running" || execution.status === "queued"
            ? "Waiting for first turn..."
            : "No conversation recorded"}
        </p>
      </div>
    );
  }

  return (
    <ScrollShadow className="h-full">
      <div className="p-6 space-y-4">
        {/* Conversation Turns */}
        {execution.turns.map((turn, index) => (
          <div key={index} className="space-y-3">
            {/* Task indicator if this is a new task */}
            {(index === 0 ||
              turn.task_index !== execution.turns[index - 1].task_index) && (
              <div className="flex items-center gap-2 py-2">
                <Divider className="flex-1" />
                <Chip size="sm" variant="flat" color="primary">
                  Task {turn.task_index + 1}
                  {scenario?.tasks[turn.task_index] && (
                    <span className="ml-1 opacity-70">
                      : {scenario.tasks[turn.task_index].task.slice(0, 30)}...
                    </span>
                  )}
                </Chip>
                <Divider className="flex-1" />
              </div>
            )}

            {/* User Message */}
            <Card className="ml-8 bg-primary-50 dark:bg-primary-900/20">
              <CardBody className="p-3">
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                    <Icon icon="heroicons:user" className="text-white text-sm" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground-500 mb-1">
                      Simulated User
                    </p>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {turn.user_message}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Assistant Message */}
            <Card className="mr-8">
              <CardBody className="p-3">
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 rounded-full bg-success flex items-center justify-center flex-shrink-0">
                    <Icon icon="heroicons:cpu-chip" className="text-white text-sm" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground-500 mb-1">Assistant</p>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {turn.assistant_message}
                      </ReactMarkdown>
                    </div>

                    {/* Tool Calls */}
                    {turn.tool_calls.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs text-foreground-500">Tools Used:</p>
                        <div className="flex flex-wrap gap-1">
                          {turn.tool_calls.map((tool, i) => (
                            <Chip key={i} size="sm" variant="flat">
                              {tool.name}
                            </Chip>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Task Completion Indicator */}
            {turn.task_completed && (
              <div className="flex items-center justify-center gap-2 py-2">
                <Chip
                  size="sm"
                  color="success"
                  variant="flat"
                  startContent={<Icon icon="heroicons:check" />}
                >
                  Task Completed: {turn.task_completed_reason}
                </Chip>
              </div>
            )}
          </div>
        ))}

        {/* Status indicator at the end */}
        {execution.status === "running" && (
          <div className="flex items-center justify-center gap-2 py-4">
            <Icon
              icon="heroicons:arrow-path"
              className="animate-spin text-primary"
            />
            <span className="text-sm text-foreground-500">
              Processing turn {execution.currentTurn + 1}...
            </span>
          </div>
        )}

        {execution.status === "completed" && (
          <div className="flex items-center justify-center gap-2 py-4">
            <Chip
              color="success"
              variant="flat"
              startContent={<Icon icon="heroicons:check" />}
            >
              Scenario Completed
            </Chip>
          </div>
        )}

        {execution.status === "failed" && (
          <div className="flex flex-col items-center justify-center gap-2 py-4">
            <Chip
              color="danger"
              variant="flat"
              startContent={<Icon icon="heroicons:x-mark" />}
            >
              Scenario Failed
            </Chip>
            {execution.error && (
              <p className="text-sm text-danger">{execution.error}</p>
            )}
          </div>
        )}

        {execution.status === "timeout" && (
          <div className="flex flex-col items-center justify-center gap-2 py-4">
            <Chip
              color="warning"
              variant="flat"
              startContent={<Icon icon="heroicons:clock" />}
            >
              Scenario Timed Out
            </Chip>
            {execution.error && (
              <p className="text-sm text-warning">{execution.error}</p>
            )}
          </div>
        )}
      </div>
    </ScrollShadow>
  );
}
