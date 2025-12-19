import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router";
import { Button, Chip, Card, CardBody, Tabs, Tab, Spinner } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore } from "../../../stores/EvalStoreContext";
import type { CheckerResultItem, ConversationMetrics, ResponseChunk, ScenarioRun, SimulationRun, SimulationStatus } from "../../../types";

const STATUS_CONFIG: Record<
  SimulationStatus,
  { color: "success" | "danger" | "warning" | "primary" | "default"; label: string }
> = {
  completed: { color: "success", label: "Completed" },
  failed: { color: "danger", label: "Failed" },
  timeout: { color: "warning", label: "Timeout" },
  running: { color: "primary", label: "Running" },
  queued: { color: "default", label: "Queued" },
  idle: { color: "default", label: "Idle" },
};

// Run summary stats component for header
function RunSummaryStats({ scenarioRuns, onRerun }: { scenarioRuns: ScenarioRun[]; onRerun: () => void }) {
  const aggregated = useMemo(() => {
    let totalTurns = 0;
    let totalTasks = 0;
    let tasksCompleted = 0;
    let estimatedUsd = 0;
    const latencies: number[] = [];
    const ttfts: number[] = [];

    for (const sr of scenarioRuns) {
      if (!sr.metrics) continue;
      const m = sr.metrics;

      totalTurns += m.total_turns ?? 0;
      totalTasks += m.total_tasks ?? 0;
      tasksCompleted += m.tasks_completed ?? 0;
      estimatedUsd += m.estimated_usd ?? 0;

      if (m.latency_avg_ms) latencies.push(m.latency_avg_ms as number);
      if (m.time_to_first_token_avg_ms) ttfts.push(m.time_to_first_token_avg_ms as number);
    }

    const successRate = totalTasks > 0 ? tasksCompleted / totalTasks : 0;
    const avgLatency = latencies.length > 0 ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;
    const avgTtft = ttfts.length > 0 ? ttfts.reduce((a, b) => a + b, 0) / ttfts.length : 0;

    return { totalTurns, totalTasks, tasksCompleted, successRate, estimatedUsd, avgLatency, avgTtft };
  }, [scenarioRuns]);

  const successColor = aggregated.successRate >= 0.9 ? "success" : aggregated.successRate >= 0.7 ? "warning" : "danger";

  return (
    <div className="flex items-center gap-6">
      <div className="flex items-center gap-5 text-sm">
        <div className="text-center">
          <p className="text-foreground-400">Turns</p>
          <p className="font-semibold">{aggregated.totalTurns}</p>
        </div>
        <div className="text-center">
          <p className="text-foreground-400">Tasks</p>
          <p className="font-semibold">{aggregated.tasksCompleted}/{aggregated.totalTasks}</p>
        </div>
        <div className="text-center">
          <p className="text-foreground-400">Success</p>
          <p className={`font-semibold text-${successColor}`}>
            {(aggregated.successRate * 100).toFixed(0)}%
          </p>
        </div>
        {aggregated.avgLatency > 0 && (
          <div className="text-center">
            <p className="text-foreground-400">Latency</p>
            <p className="font-semibold">{aggregated.avgLatency.toFixed(0)}ms</p>
          </div>
        )}
        {aggregated.avgTtft > 0 && (
          <div className="text-center">
            <p className="text-foreground-400">TTFT</p>
            <p className="font-semibold">{aggregated.avgTtft.toFixed(0)}ms</p>
          </div>
        )}
        <div className="text-center">
          <p className="text-foreground-400">Cost</p>
          <p className="font-semibold">${aggregated.estimatedUsd.toFixed(4)}</p>
        </div>
      </div>
      <Button
        color="primary"
        variant="flat"
        onPress={onRerun}
        startContent={<Icon icon="heroicons:arrow-path" />}
      >
        Rerun
      </Button>
    </div>
  );
}

// Transform API response (snake_case) to frontend types (camelCase)
function transformRunResponse(data: any): SimulationRun {
  return {
    id: data.id,
    timestamp: data.timestamp,
    version: data.version || "current",
    status: data.status,
    scenarioRuns: (data.scenario_runs || []).map((sr: any) => ({
      id: sr.id,
      scenarioName: sr.scenario_name,
      persona: sr.persona || null,
      status: sr.status,
      startTime: sr.start_time,
      endTime: sr.end_time,
      turns: (sr.turns || []).map((t: any) => ({
        turn_index: t.turn_index,
        task_index: t.task_index,
        user_message: t.user_message,
        assistant_message: t.assistant_message,
        tool_calls: t.tool_calls || [],
        task_completed: t.task_completed,
        task_completed_reason: t.task_completed_reason,
        token_usage: t.token_usage,
        latency_ms: t.latency_ms,
        checkers: (t.checkers || []).map((c: any) => ({
          type: c.type,
          completed: c.completed,
          reason: c.reason,
        })),
        checker_mode: t.checker_mode || "all",
      })),
      tasks: (sr.tasks || []).map((t: any) => ({
        task_index: t.task_index,
        description: t.description,
        completed: t.completed,
        turns_taken: t.turns_taken,
        final_reason: t.final_reason,
      })),
      responseChunks: (sr.response_chunks || []).map((c: any) => ({
        turn_index: c.turn_index,
        task_index: c.task_index,
        chunk_index: c.chunk_index,
        chunk_type: c.chunk_type,
        chunk_data: c.chunk_data,
      })),
      metrics: sr.metrics,
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
    group: data.group || null,
    totalScenarios: data.total_scenarios || 0,
    completedScenarios: data.completed_scenarios || 0,
    failedScenarios: data.failed_scenarios || 0,
    totalTokens: data.total_tokens || 0,
    totalCostUsd: data.total_cost_usd || 0,
    overallSuccessRate: data.overall_success_rate || 0,
  };
}

export function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const { client } = useRagbitsContext();
  const simulationRuns = useEvalStore((s) => s.simulationRuns);

  const [apiRun, setApiRun] = useState<SimulationRun | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedScenarioIndex, setSelectedScenarioIndex] = useState(0);
  const [fetchedBuffers, setFetchedBuffers] = useState<Set<string>>(new Set());

  // Find run in store (for live runs)
  const storeRun = simulationRuns.find((r) => r.id === runId) ?? null;

  // Fetch full run data from API (only once on mount)
  useEffect(() => {
    async function loadRun() {
      if (!runId) return;

      setIsLoading(true);
      try {
        const response = await client.makeRequest(
          `/api/eval/runs/${runId}` as "/api/config"
        );
        setApiRun(transformRunResponse(response));
      } catch (error) {
        // API 404 is expected for live runs - use store data instead
        console.debug("Run not found in API, using store data");
      } finally {
        setIsLoading(false);
      }
    }

    loadRun();
  }, [runId, client]); // Don't include simulationRuns - causes infinite loop

  // Use API data if available, otherwise fall back to store (for live runs)
  const run = apiRun ?? storeRun;

  const selectedScenarioRun = run?.scenarioRuns[selectedScenarioIndex] ?? null;

  // Fetch buffered events for live runs when selecting a scenario
  const handleSelectScenario = useCallback(async (index: number) => {
    setSelectedScenarioIndex(index);

    // Only fetch for live runs (storeRun exists and apiRun is null)
    if (!runId || apiRun || !storeRun) return;

    const scenarioRun = storeRun.scenarioRuns[index];
    if (!scenarioRun?.id || fetchedBuffers.has(scenarioRun.id)) return;

    // Try to fetch buffered events
    try {
      const response = await client.makeRequest(
        `/api/eval/progress/${runId}/buffer/${scenarioRun.id}` as "/api/config"
      );
      const events = (response as { events?: unknown[] })?.events ?? [];

      if (events.length > 0) {
        // Mark this buffer as fetched
        setFetchedBuffers((prev) => new Set(prev).add(scenarioRun.id));
        console.debug(`Fetched ${events.length} buffered events for ${scenarioRun.id}`);
      }
    } catch (error) {
      // Buffered events might not be available - that's okay
      console.debug("Could not fetch buffered events:", error);
    }
  }, [runId, apiRun, storeRun, fetchedBuffers, client]);

  const handleBack = useCallback(() => {
    navigate("/runs");
  }, [navigate]);

  const handleRerun = useCallback(() => {
    if (run) {
      const scenarioNames = run.scenarioRuns
        .map((sr) => sr.scenarioName)
        .join(",");
      navigate(`/new?scenarios=${encodeURIComponent(scenarioNames)}`);
    }
  }, [navigate, run]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <Icon
          icon="heroicons:exclamation-triangle"
          className="text-6xl text-danger mb-4"
        />
        <p className="text-foreground-500">Run not found</p>
        <Button className="mt-4" onPress={handleBack}>
          Back to Runs
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-divider px-6 py-4">
        <div className="flex items-center gap-4">
          <Button
            isIconOnly
            variant="light"
            onPress={handleBack}
            aria-label="Back"
          >
            <Icon icon="heroicons:arrow-left" className="text-xl" />
          </Button>
          <div>
            <h2 className="text-xl font-semibold text-foreground">
              Simulation Run
            </h2>
            <div className="flex items-center gap-2 text-sm text-foreground-500">
              <span>{new Date(run.timestamp).toLocaleString()}</span>
              <span className="font-mono">{run.version}</span>
              <Chip
                size="sm"
                color={STATUS_CONFIG[run.status].color}
                variant="flat"
              >
                {STATUS_CONFIG[run.status].label}
              </Chip>
            </div>
          </div>
        </div>
        <RunSummaryStats scenarioRuns={run.scenarioRuns} onRerun={handleRerun} />
      </div>

      {/* Main content: List + Panel */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Scenario list */}
        <aside className="w-96 flex-shrink-0 border-r border-divider overflow-y-auto p-4">
          <h3 className="text-sm font-semibold text-foreground-500 uppercase tracking-wide mb-3">
            Scenarios ({run.scenarioRuns.length})
          </h3>
          <div className="space-y-2">
            {run.scenarioRuns.map((sr, index) => (
              <Card
                key={sr.id || sr.scenarioName}
                isPressable
                onPress={() => handleSelectScenario(index)}
                className={`w-full ${
                  selectedScenarioIndex === index
                    ? "border-2 border-primary"
                    : ""
                }`}
              >
                <CardBody className="p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{sr.scenarioName}</p>
                      <div className="flex items-center gap-2 text-xs text-foreground-400">
                        <span>{sr.turns.length} turns, {sr.tasks.length} tasks</span>
                        {sr.persona && (
                          <Chip size="sm" variant="flat" className="text-xs">
                            {sr.persona}
                          </Chip>
                        )}
                      </div>
                    </div>
                    <Chip
                      size="sm"
                      color={STATUS_CONFIG[sr.status].color}
                      variant="flat"
                    >
                      {STATUS_CONFIG[sr.status].label}
                    </Chip>
                  </div>
                  {sr.metrics && (
                    <div className="flex items-center gap-3 mt-2 text-xs text-foreground-500">
                      <span>{Math.round(sr.metrics.success_rate * 100)}%</span>
                      <span>{sr.metrics.total_tokens} tokens</span>
                    </div>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>
        </aside>

        {/* Right: Scenario detail panel */}
        <main className="flex-1 min-h-0 overflow-hidden">
          {selectedScenarioRun ? (
            <ScenarioRunPanel scenarioRun={selectedScenarioRun} />
          ) : (
            <div className="flex h-full items-center justify-center text-foreground-500">
              Select a scenario to view details
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function ScenarioRunPanel({ scenarioRun }: { scenarioRun: ScenarioRun }) {
  const [viewMode, setViewMode] = useState<"conversation" | "responses" | "metrics">(
    "conversation",
  );

  const responseChunksCount = scenarioRun.responseChunks?.length || 0;

  return (
    <div className="flex h-full flex-col">
      {/* Scenario header */}
      <div className="border-b border-divider px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">{scenarioRun.scenarioName}</h3>
            <div className="flex items-center gap-2 text-sm text-foreground-500">
              <span>
                {scenarioRun.tasks.filter((t) => t.completed).length}/
                {scenarioRun.tasks.length} tasks completed
              </span>
              {scenarioRun.persona && (
                <>
                  <span>•</span>
                  <Chip size="sm" variant="flat">
                    {scenarioRun.persona}
                  </Chip>
                </>
              )}
            </div>
          </div>
        </div>
        {scenarioRun.error && (
          <div className="mt-2 p-2 bg-danger-50 dark:bg-danger-900/20 rounded-lg text-danger text-sm">
            {scenarioRun.error}
          </div>
        )}
      </div>

      {/* View toggle */}
      <div className="border-b border-divider px-6 py-2">
        <Tabs
          selectedKey={viewMode}
          onSelectionChange={(key) =>
            setViewMode(key as "conversation" | "responses" | "metrics")
          }
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
                {responseChunksCount > 0 && (
                  <Chip size="sm" variant="flat" className="ml-1">
                    {responseChunksCount}
                  </Chip>
                )}
              </div>
            }
          />
          <Tab
            key="metrics"
            title={
              <div className="flex items-center gap-2">
                <Icon icon="heroicons:chart-bar" />
                <span>Metrics</span>
              </div>
            }
          />
        </Tabs>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto p-6">
        {viewMode === "conversation" ? (
          <ConversationView turns={scenarioRun.turns} tasks={scenarioRun.tasks} />
        ) : viewMode === "responses" ? (
          <ResponsesView scenarioRun={scenarioRun} />
        ) : (
          <MetricsView metrics={scenarioRun.metrics} />
        )}
      </div>
    </div>
  );
}

function CheckerResultsList({ checkers }: { checkers: CheckerResultItem[] }) {
  if (!checkers || checkers.length === 0) return null;

  return (
    <div className="mt-2 space-y-2">
      {checkers.map((checker, idx) => (
        <div key={idx} className={`flex items-start gap-2 p-2 rounded ${checker.completed ? "bg-success/10" : "bg-default-100"}`}>
          <Icon
            icon={checker.completed ? "heroicons:check-circle" : "heroicons:x-circle"}
            className={`text-sm flex-shrink-0 mt-0.5 ${checker.completed ? "text-success" : "text-default-400"}`}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Chip size="sm" variant="bordered" className="text-xs">
                {checker.type}
              </Chip>
            </div>
            <p className="text-xs text-foreground-500 mt-1">{checker.reason}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function ConversationView({
  turns,
  tasks,
}: {
  turns: ScenarioRun["turns"];
  tasks: ScenarioRun["tasks"];
}) {
  if (turns.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-foreground-500">
        No conversation data
      </div>
    );
  }

  // Get task description by index
  const getTask = (taskIndex: number) => tasks.find((t) => t.task_index === taskIndex);

  return (
    <div className="space-y-4">
      {turns.map((turn, index) => {
        const prevTaskIndex = index > 0 ? turns[index - 1].task_index : -1;
        const isNewTask = turn.task_index !== prevTaskIndex;
        const task = isNewTask ? getTask(turn.task_index) : null;

        return (
          <div key={index} className="space-y-3">
            {/* Task marker */}
            {isNewTask && (
              <div className="flex items-center gap-3 py-3">
                <div className="flex-1 h-px bg-primary/30" />
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20">
                  <Icon icon="heroicons:flag" className="text-primary text-sm" />
                  <span className="text-sm font-medium text-primary">
                    Task {turn.task_index + 1}
                  </span>
                </div>
                <div className="flex-1 h-px bg-primary/30" />
              </div>
            )}
            {isNewTask && task && (
              <div className="mx-4 p-3 rounded-lg bg-primary/5 border border-primary/20 mb-4">
                <p className="text-sm text-foreground-600">{task.description}</p>
              </div>
            )}

            {/* User message */}
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                <Icon icon="heroicons:user" className="text-white text-sm" />
              </div>
              <div className="flex-1 p-3 rounded-lg bg-content2">
                <p className="text-xs text-foreground-500 mb-1">Simulated User</p>
                <p>{turn.user_message}</p>
              </div>
            </div>

            {/* Assistant message */}
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                <Icon icon="heroicons:cpu-chip" className="text-white text-sm" />
              </div>
              <div className="flex-1 p-3 rounded-lg bg-content2">
                <p className="text-xs text-foreground-500 mb-1">Assistant</p>
                <p className="whitespace-pre-wrap">{turn.assistant_message}</p>
                {turn.tool_calls.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-divider">
                    <p className="text-xs text-foreground-500 mb-1">Tool calls:</p>
                    <div className="flex flex-wrap gap-1">
                      {turn.tool_calls.map((tc, tcIndex) => (
                        <Chip key={tcIndex} size="sm" variant="flat">
                          {tc.name}
                        </Chip>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Checker Decision */}
            <div className={`mx-4 p-3 rounded-lg border ${turn.task_completed ? "border-success bg-success/5" : "border-default-200 bg-default-50"}`}>
              <div className="flex items-start gap-2">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${turn.task_completed ? "bg-success" : "bg-default-300"}`}>
                  <Icon
                    icon={turn.task_completed ? "heroicons:check" : "heroicons:x-mark"}
                    className="text-white text-sm"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <p className="text-xs font-medium text-foreground-500">Checker Decision</p>
                    <Chip size="sm" color={turn.task_completed ? "success" : "default"} variant="flat">
                      {turn.task_completed ? "Completed" : "Not Completed"}
                    </Chip>
                    {(turn.checkers?.length ?? 0) > 1 && (
                      <Chip size="sm" variant="bordered" className="text-xs">
                        mode: {turn.checker_mode ?? "all"}
                      </Chip>
                    )}
                  </div>
                  {turn.task_completed_reason && (
                    <p className="text-sm text-foreground-600 mb-2">{turn.task_completed_reason}</p>
                  )}
                  {/* Individual checker results */}
                  <CheckerResultsList checkers={turn.checkers ?? []} />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Chunk type configuration for styling
const CHUNK_TYPE_CONFIG: Record<
  string,
  { color: "primary" | "success" | "warning" | "secondary" | "danger" | "default"; icon: string; label: string }
> = {
  text: { color: "primary", icon: "heroicons:document-text", label: "Text" },
  reference: { color: "success", icon: "heroicons:bookmark", label: "Reference" },
  tool_call: { color: "warning", icon: "heroicons:wrench", label: "Tool Call" },
  usage: { color: "secondary", icon: "heroicons:chart-bar", label: "Usage" },
  live_update: { color: "primary", icon: "heroicons:arrow-path", label: "Live Update" },
  checker_decision: { color: "secondary", icon: "heroicons:scale", label: "Checker" },
  error: { color: "danger", icon: "heroicons:exclamation-triangle", label: "Error" },
  unknown: { color: "default", icon: "heroicons:question-mark-circle", label: "Unknown" },
};

function getChunkConfig(chunkType: string) {
  return CHUNK_TYPE_CONFIG[chunkType] || CHUNK_TYPE_CONFIG.unknown;
}

// Aggregated text chunks type
interface AggregatedTextChunk {
  _aggregated: true;
  count: number;
  turn_index: number;
  chunk_index: number;
}

function isAggregatedChunk(chunk: ResponseChunk | AggregatedTextChunk): chunk is AggregatedTextChunk {
  return "_aggregated" in chunk && chunk._aggregated === true;
}

function AggregatedTextCard({ chunk }: { chunk: AggregatedTextChunk }) {
  const config = getChunkConfig("text");
  return (
    <Card className="shadow-sm bg-default-50">
      <CardBody className="p-3">
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-${config.color}/10`}>
            <Icon icon={config.icon} className={`text-${config.color} text-lg`} />
          </div>
          <div className="flex items-center gap-2">
            <Chip size="sm" color={config.color} variant="flat">
              {chunk.count} text chunk{chunk.count > 1 ? "s" : ""}
            </Chip>
            <span className="text-xs text-foreground-500">Turn {chunk.turn_index + 1}</span>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function ResponsesView({ scenarioRun }: { scenarioRun: ScenarioRun }) {
  const responseChunks = scenarioRun.responseChunks || [];

  // Aggregate consecutive text chunks
  const aggregatedChunks = useMemo(() => {
    const result: (ResponseChunk | AggregatedTextChunk)[] = [];
    let textCount = 0;
    let firstTextChunk: ResponseChunk | null = null;

    for (const chunk of responseChunks) {
      if (chunk.chunk_type === "text") {
        if (textCount === 0) {
          firstTextChunk = chunk;
        }
        textCount++;
      } else {
        if (textCount > 0 && firstTextChunk) {
          result.push({
            _aggregated: true,
            count: textCount,
            turn_index: firstTextChunk.turn_index,
            chunk_index: firstTextChunk.chunk_index,
          });
          textCount = 0;
          firstTextChunk = null;
        }
        result.push(chunk);
      }
    }

    // Don't forget trailing text chunks
    if (textCount > 0 && firstTextChunk) {
      result.push({
        _aggregated: true,
        count: textCount,
        turn_index: firstTextChunk.turn_index,
        chunk_index: firstTextChunk.chunk_index,
      });
    }

    return result;
  }, [responseChunks]);

  if (responseChunks.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <Icon icon="heroicons:squares-2x2" className="text-5xl text-foreground-300 mb-4" />
        <h3 className="text-lg font-medium text-foreground">No Response Chunks</h3>
        <p className="text-sm text-foreground-500 mt-2">
          Response chunks are only available for live runs
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold">Response Stream</h4>
        <Chip size="sm" variant="flat">
          {responseChunks.length} chunks
        </Chip>
      </div>
      {aggregatedChunks.map((chunk, index) =>
        isAggregatedChunk(chunk) ? (
          <AggregatedTextCard key={`agg-${chunk.turn_index}-${chunk.chunk_index}`} chunk={chunk} />
        ) : (
          <Card key={index} className="shadow-sm">
            <CardBody className="p-3">
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-${getChunkConfig(chunk.chunk_type).color}/10`}>
                  <Icon icon={getChunkConfig(chunk.chunk_type).icon} className={`text-${getChunkConfig(chunk.chunk_type).color} text-lg`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <Chip size="sm" color={getChunkConfig(chunk.chunk_type).color} variant="flat">
                      {getChunkConfig(chunk.chunk_type).label}
                    </Chip>
                    <span className="text-xs text-foreground-500">
                      Turn {chunk.turn_index + 1} • Task {chunk.task_index + 1}
                    </span>
                  </div>
                  <pre className="text-xs p-2 bg-default-100 rounded overflow-auto max-h-32">
                    {JSON.stringify(chunk.chunk_data, null, 2)}
                  </pre>
                </div>
              </div>
            </CardBody>
          </Card>
        )
      )}
    </div>
  );
}

// Format metric value for display
function formatMetricValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "N/A";

  if (typeof value === "number") {
    // Percentage values
    if (key.includes("rate") || key.includes("success")) {
      return `${Math.round(value * 100)}%`;
    }
    // Cost values
    if (key.includes("cost") || key.includes("usd")) {
      return `$${value.toFixed(4)}`;
    }
    // Latency/time values
    if (key.includes("_ms") || key.includes("latency") || key.includes("time_to")) {
      return `${value.toFixed(1)} ms`;
    }
    // Token counts and other numbers
    if (Number.isInteger(value)) {
      return value.toLocaleString();
    }
    return value.toFixed(2);
  }

  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(", ") : "None";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

// Format metric key for display (snake_case to Title Case)
function formatMetricLabel(key: string): string {
  return key
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

// Core Metrics Card - unified display
function CoreMetricsCard({ metrics }: { metrics: Record<string, unknown> }) {
  const successRate = (metrics.success_rate as number) ?? 0;
  const successPercent = successRate <= 1 ? successRate * 100 : successRate;
  const successColor = successPercent >= 90 ? "success" : successPercent >= 70 ? "warning" : "danger";

  return (
    <Card className="bg-gradient-to-br from-content1 to-content2">
      <CardBody className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon="heroicons:chart-pie" className="text-lg text-primary" />
          <h4 className="font-semibold">Overview</h4>
        </div>
        <div className="grid grid-cols-4 gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold">{(metrics.total_turns as number) ?? 0}</p>
            <p className="text-xs text-foreground-500 mt-1">Total Turns</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold">
              {(metrics.tasks_completed as number) ?? 0}/{(metrics.total_tasks as number) ?? 0}
            </p>
            <p className="text-xs text-foreground-500 mt-1">Tasks Completed</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-2">
              <div className={`w-3 h-3 rounded-full bg-${successColor}`} />
              <p className="text-3xl font-bold">{successPercent.toFixed(0)}%</p>
            </div>
            <p className="text-xs text-foreground-500 mt-1">Success Rate</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold">${((metrics.estimated_usd as number) ?? 0).toFixed(4)}</p>
            <p className="text-xs text-foreground-500 mt-1">Estimated Cost</p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

// Latency Metrics Card - unified display
function LatencyMetricsCard({ metrics }: { metrics: Record<string, unknown> }) {
  const avgLatency = (metrics.latency_avg_ms as number) ?? 0;
  const minLatency = (metrics.latency_min_ms as number) ?? 0;
  const maxLatency = (metrics.latency_max_ms as number) ?? 0;
  const ttftAvg = (metrics.time_to_first_token_avg_ms as number) ?? 0;
  const ttftMin = (metrics.time_to_first_token_min_ms as number) ?? 0;
  const ttftMax = (metrics.time_to_first_token_max_ms as number) ?? 0;

  return (
    <Card>
      <CardBody className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon="heroicons:clock" className="text-lg text-warning" />
          <h4 className="font-semibold">Latency</h4>
        </div>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <p className="text-xs text-foreground-500 mb-2">Response Time</p>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-bold">{avgLatency.toFixed(0)}</p>
              <p className="text-sm text-foreground-500">ms avg</p>
            </div>
            <div className="flex gap-4 mt-2 text-xs text-foreground-400">
              <span>Min: {minLatency.toFixed(0)}ms</span>
              <span>Max: {maxLatency.toFixed(0)}ms</span>
            </div>
          </div>
          <div>
            <p className="text-xs text-foreground-500 mb-2">Time to First Token</p>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-bold">{ttftAvg.toFixed(0)}</p>
              <p className="text-sm text-foreground-500">ms avg</p>
            </div>
            <div className="flex gap-4 mt-2 text-xs text-foreground-400">
              <span>Min: {ttftMin.toFixed(0)}ms</span>
              <span>Max: {ttftMax.toFixed(0)}ms</span>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

// Token Usage Card - unified display
function TokenUsageCard({ metrics }: { metrics: Record<string, unknown> }) {
  const total = (metrics.tokens_total as number) ?? (metrics.total_tokens as number) ?? 0;
  const prompt = (metrics.tokens_prompt as number) ?? (metrics.prompt_tokens as number) ?? 0;
  const completion = (metrics.tokens_completion as number) ?? (metrics.completion_tokens as number) ?? 0;
  const avgPerTurn = (metrics.tokens_avg_per_turn as number) ?? 0;

  const promptPercent = total > 0 ? (prompt / total) * 100 : 0;

  return (
    <Card>
      <CardBody className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon="heroicons:calculator" className="text-lg text-secondary" />
          <h4 className="font-semibold">Token Usage</h4>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex-1">
            <p className="text-3xl font-bold">{total.toLocaleString()}</p>
            <p className="text-xs text-foreground-500 mt-1">Total Tokens</p>
          </div>
          <div className="flex-1">
            <div className="h-3 rounded-full bg-default-200 overflow-hidden">
              <div
                className="h-full bg-primary rounded-full"
                style={{ width: `${promptPercent}%` }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs">
              <span className="text-primary">{prompt.toLocaleString()} prompt</span>
              <span className="text-foreground-500">{completion.toLocaleString()} completion</span>
            </div>
          </div>
          {avgPerTurn > 0 && (
            <div className="text-center">
              <p className="text-xl font-bold">{avgPerTurn.toLocaleString()}</p>
              <p className="text-xs text-foreground-500">avg/turn</p>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

// Tool Usage Card - unified display
function ToolUsageCard({ metrics }: { metrics: Record<string, unknown> }) {
  const totalCalls = (metrics.tools_total_calls as number) ?? 0;
  const uniqueTools = metrics.tools_unique as string[] | string | undefined;
  const toolCounts = metrics.tools_counts as Record<string, number> | undefined;

  const uniqueList: string[] = Array.isArray(uniqueTools)
    ? uniqueTools
    : typeof uniqueTools === "string"
      ? uniqueTools.split(",").map((s) => s.trim()).filter(Boolean)
      : [];

  return (
    <Card>
      <CardBody className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon="heroicons:wrench-screwdriver" className="text-lg text-warning" />
          <h4 className="font-semibold">Tool Usage</h4>
        </div>
        <div className="flex items-start gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold">{totalCalls}</p>
            <p className="text-xs text-foreground-500 mt-1">Total Calls</p>
          </div>
          <div className="flex-1">
            <p className="text-xs text-foreground-500 mb-2">Tools Used</p>
            <div className="flex flex-wrap gap-2">
              {toolCounts ? (
                Object.entries(toolCounts).map(([tool, count]) => (
                  <Chip key={tool} size="sm" variant="flat">
                    {tool} <span className="text-foreground-400 ml-1">×{count}</span>
                  </Chip>
                ))
              ) : uniqueList.length > 0 ? (
                uniqueList.map((tool) => (
                  <Chip key={tool} size="sm" variant="flat">{tool}</Chip>
                ))
              ) : (
                <span className="text-foreground-500 text-sm">No tools used</span>
              )}
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

// DeepEval Scores Card - unified display
function DeepEvalCard({ metrics }: { metrics: Record<string, unknown> }) {
  const scores: { key: string; label: string; value: number; reason?: string }[] = [];

  for (const [key, value] of Object.entries(metrics)) {
    if (key.startsWith("deepeval_") && !key.includes("reason") && typeof value === "number") {
      const label = key.replace("deepeval_", "").split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
      const reasonKey = `${key}_reason`;
      scores.push({
        key,
        label,
        value,
        reason: metrics[reasonKey] as string | undefined,
      });
    }
  }

  if (scores.length === 0) return null;

  return (
    <Card>
      <CardBody className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon="heroicons:academic-cap" className="text-lg text-success" />
          <h4 className="font-semibold">DeepEval Scores</h4>
        </div>
        <div className="space-y-4">
          {scores.map(({ key, label, value, reason }) => {
            const percent = value <= 1 ? value * 100 : value;
            const color = percent >= 90 ? "success" : percent >= 70 ? "warning" : "danger";
            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{label}</span>
                  <span className={`text-sm font-bold text-${color}`}>{percent.toFixed(0)}%</span>
                </div>
                <div className="h-2 rounded-full bg-default-200 overflow-hidden">
                  <div
                    className={`h-full bg-${color} rounded-full transition-all`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
                {reason && (
                  <p className="text-xs text-foreground-500 mt-2 line-clamp-2">{reason}</p>
                )}
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}

// Other Metrics - generic grid display
function OtherMetricsCard({ metrics }: { metrics: Record<string, unknown> }) {
  const entries = Object.entries(metrics);
  if (entries.length === 0) return null;

  return (
    <Card>
      <CardBody className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Icon icon="heroicons:squares-plus" className="text-lg text-foreground-500" />
          <h4 className="font-semibold">Other Metrics</h4>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {entries.map(([key, value]) => (
            <div key={key}>
              <p className="text-xs text-foreground-400">{formatMetricLabel(key)}</p>
              <p className="text-lg font-semibold">{formatMetricValue(key, value)}</p>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function MetricsView({ metrics }: { metrics: ConversationMetrics | null }) {
  if (!metrics) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-center">
        <Icon icon="heroicons:chart-bar" className="text-5xl text-foreground-300 mb-4" />
        <h3 className="text-lg font-medium text-foreground">No Metrics Available</h3>
        <p className="text-sm text-foreground-500 mt-2">
          Metrics will be available after the simulation completes
        </p>
      </div>
    );
  }

  const m = metrics as Record<string, unknown>;

  // Group metrics
  const coreMetrics: Record<string, unknown> = {};
  const latencyMetrics: Record<string, unknown> = {};
  const tokenMetrics: Record<string, unknown> = {};
  const toolMetrics: Record<string, unknown> = {};
  const deepevalMetrics: Record<string, unknown> = {};
  const otherMetrics: Record<string, unknown> = {};

  const coreKeys = ["total_turns", "total_tasks", "tasks_completed", "success_rate", "estimated_usd"];

  for (const [key, value] of Object.entries(m)) {
    if (coreKeys.includes(key)) {
      coreMetrics[key] = value;
    } else if (key.startsWith("latency") || key.startsWith("time_to_first")) {
      latencyMetrics[key] = value;
    } else if (key.startsWith("tokens") || key === "prompt_tokens" || key === "completion_tokens" || key === "total_tokens") {
      tokenMetrics[key] = value;
    } else if (key.startsWith("tools")) {
      toolMetrics[key] = value;
    } else if (key.startsWith("deepeval")) {
      deepevalMetrics[key] = value;
    } else {
      otherMetrics[key] = value;
    }
  }

  const hasLatency = Object.keys(latencyMetrics).length > 0;
  const hasTokens = Object.keys(tokenMetrics).length > 0;
  const hasTools = Object.keys(toolMetrics).length > 0;
  const hasDeepeval = Object.keys(deepevalMetrics).length > 0;
  const hasOther = Object.keys(otherMetrics).length > 0;

  return (
    <div className="space-y-4">
      <CoreMetricsCard metrics={coreMetrics} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {hasLatency && <LatencyMetricsCard metrics={latencyMetrics} />}
        {hasTokens && <TokenUsageCard metrics={tokenMetrics} />}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {hasTools && <ToolUsageCard metrics={toolMetrics} />}
        {hasDeepeval && <DeepEvalCard metrics={deepevalMetrics} />}
      </div>

      {hasOther && <OtherMetricsCard metrics={otherMetrics} />}
    </div>
  );
}


