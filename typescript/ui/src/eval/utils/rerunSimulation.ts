import type { RagbitsClient } from "@ragbits/api-client";
import type { SimulationRun, ProgressUpdate, ScenarioSummary } from "../types";
import { selectProgress } from "../stores/evalStore";

type StoreApi = {
  getState: () => {
    simulationRuns: SimulationRun[];
    config: { available_scenarios: ScenarioSummary[] } | null;
    simulationConfig: SimulationRun["config"];
    actions: {
      addSimulationRun: (run: SimulationRun) => void;
      startExecution: (runId: string, scenarioNames: string[]) => void;
      handleProgressUpdate: (update: ProgressUpdate) => void;
      updateSimulationRun: (runId: string, updates: Partial<SimulationRun>) => void;
    };
  };
};

export async function rerunSimulation(
  run: SimulationRun,
  client: RagbitsClient,
  storeApi: StoreApi,
): Promise<string> {
  const scenarioNames = [...new Set(run.scenarioRuns.map((sr) => sr.scenarioName))];
  const personas = [...new Set(run.scenarioRuns.map((sr) => sr.persona).filter(Boolean))] as string[];
  const config = run.config ?? storeApi.getState().simulationConfig;

  const response = await fetch(`${client.getBaseUrl()}/api/eval/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario_names: scenarioNames,
      personas: personas.length > 0 ? personas : null,
      config,
    }),
  });

  if (!response.ok) throw new Error(`Failed: ${response.statusText}`);
  const data = await response.json();
  const newRunId = data.run_id;

  // Create initial store entry
  const availableScenarios = storeApi.getState().config?.available_scenarios ?? [];
  const newScenarioRuns = [];
  const personasForMatrix: (string | null)[] = personas.length > 0 ? personas : [null];
  for (const name of scenarioNames) {
    const taskCount = availableScenarios.find((s) => s.name === name)?.num_tasks ?? 0;
    for (const persona of personasForMatrix) {
      newScenarioRuns.push({
        id: `${newRunId}_${name}${persona ? `:${persona}` : ""}`,
        scenarioName: name,
        persona,
        status: "queued" as const,
        startTime: new Date().toISOString(),
        endTime: null,
        turns: [],
        tasks: [],
        metrics: {
          total_turns: 0, total_tasks: taskCount, tasks_completed: 0,
          success_rate: 0, total_tokens: 0, prompt_tokens: 0,
          completion_tokens: 0, estimated_usd: 0,
        },
        error: null,
      });
    }
  }

  storeApi.getState().actions.addSimulationRun({
    id: newRunId,
    timestamp: new Date().toISOString(),
    version: "current",
    status: "running",
    config,
    group: run.group,
    scenarioRuns: newScenarioRuns,
    totalScenarios: newScenarioRuns.length,
    completedScenarios: 0, failedScenarios: 0,
    totalTokens: 0, totalCostUsd: 0, overallSuccessRate: 0,
  });
  storeApi.getState().actions.startExecution(newRunId, scenarioNames);

  // Connect SSE
  const eventSource = new EventSource(`${client.getBaseUrl()}/api/eval/progress/${newRunId}`);
  eventSource.onmessage = (event) => {
    try {
      const update = JSON.parse(event.data);
      storeApi.getState().actions.handleProgressUpdate(update);

      const currentRun = storeApi.getState().simulationRuns.find((r) => r.id === newRunId);
      if (currentRun) {
        let scenarioIndex = currentRun.scenarioRuns.findIndex((sr) => sr.id === update.scenario_run_id);
        if (scenarioIndex === -1) {
          scenarioIndex = currentRun.scenarioRuns.findIndex(
            (sr) => sr.scenarioName === update.scenario_name &&
              (sr.persona ?? null) === (update.persona ?? null) &&
              !sr.id.startsWith("sr_")
          );
        }
        if (scenarioIndex !== -1) {
          const updatedRuns = [...currentRun.scenarioRuns];
          const sr = { ...updatedRuns[scenarioIndex] };
          if (update.scenario_run_id && sr.id !== update.scenario_run_id) sr.id = update.scenario_run_id;

          const metrics = sr.metrics ?? { total_turns: 0, total_tasks: 0, tasks_completed: 0, success_rate: 0, total_tokens: 0, prompt_tokens: 0, completion_tokens: 0, estimated_usd: 0 };

          if (update.type === "status") { sr.status = update.status; }
          else if (update.type === "turn") {
            sr.status = "running";
            sr.turns = [...sr.turns, { turn_index: update.turn_index, task_index: update.task_index, user_message: update.user_message, assistant_message: update.assistant_message, tool_calls: update.tool_calls, task_completed: update.task_completed, task_completed_reason: update.task_completed_reason, token_usage: null, latency_ms: null, checkers: update.checkers, checker_mode: update.checker_mode }];
            metrics.total_turns = sr.turns.length;
            sr.metrics = { ...metrics };
          } else if (update.type === "task_complete") {
            metrics.tasks_completed = (metrics.tasks_completed ?? 0) + 1;
            metrics.success_rate = metrics.total_tasks > 0 ? metrics.tasks_completed / metrics.total_tasks : 0;
            sr.metrics = { ...metrics };
          } else if (update.type === "response_chunk") {
            if (!sr.responseChunks) sr.responseChunks = [];
            sr.responseChunks = [...sr.responseChunks, { turn_index: update.turn_index, task_index: update.task_index, chunk_index: sr.responseChunks.length, chunk_type: update.chunk_type, chunk_data: update.chunk_data, timestamp: Date.now() }];
            if (update.chunk_type === "usage") {
              const usage = update.chunk_data as Record<string, number>;
              metrics.total_tokens = (metrics.total_tokens ?? 0) + (usage.total_tokens ?? 0);
              metrics.prompt_tokens = (metrics.prompt_tokens ?? 0) + (usage.prompt_tokens ?? 0);
              metrics.completion_tokens = (metrics.completion_tokens ?? 0) + (usage.completion_tokens ?? 0);
              metrics.estimated_usd = (metrics.estimated_usd ?? 0) + (usage.estimated_cost ?? 0);
              sr.metrics = { ...metrics };
            }
          } else if (update.type === "complete") {
            sr.status = update.status;
            sr.endTime = new Date().toISOString();
            sr.metrics = { ...metrics, total_turns: update.total_turns, total_tasks: update.total_tasks, tasks_completed: update.tasks_completed, success_rate: update.success_rate };

            // Fetch full metrics for this completed scenario
            (async () => { try {
              const fullRun = await client.makeRequest(`/api/eval/runs/${newRunId}` as "/api/config");
              const d = fullRun as any;
              const fullSr = d?.scenario_runs?.find((s: any) => s.id === update.scenario_run_id);
              if (fullSr?.metrics) {
                const cur = storeApi.getState().simulationRuns.find((r) => r.id === newRunId);
                if (cur) {
                  const idx2 = cur.scenarioRuns.findIndex((s) => s.id === update.scenario_run_id);
                  if (idx2 !== -1) {
                    const upd = [...cur.scenarioRuns];
                    upd[idx2] = {
                      ...upd[idx2],
                      metrics: fullSr.metrics,
                      turns: (fullSr.turns || []).map((t: any) => ({ turn_index: t.turn_index, task_index: t.task_index, user_message: t.user_message, assistant_message: t.assistant_message, tool_calls: t.tool_calls || [], task_completed: t.task_completed, task_completed_reason: t.task_completed_reason, token_usage: t.token_usage, latency_ms: t.latency_ms, checkers: t.checkers, checker_mode: t.checker_mode })),
                      tasks: (fullSr.tasks || []).map((t: any) => ({ task_index: t.task_index, description: t.description, completed: t.completed, turns_taken: t.turns_taken, final_reason: t.final_reason })),
                      responseChunks: upd[idx2].responseChunks,
                    };
                    storeApi.getState().actions.updateSimulationRun(newRunId, { scenarioRuns: upd });
                  }
                }
              }
            } catch { /* non-critical */ } })();
          } else if (update.type === "error") {
            sr.status = "failed"; sr.error = update.error; sr.endTime = new Date().toISOString();
          }

          updatedRuns[scenarioIndex] = sr;
          const completed = updatedRuns.filter((r) => r.status === "completed").length;
          const failed = updatedRuns.filter((r) => r.status === "failed" || r.status === "timeout").length;
          const allDone = completed + failed === updatedRuns.length;
          storeApi.getState().actions.updateSimulationRun(newRunId, {
            scenarioRuns: updatedRuns, status: allDone ? (failed > 0 ? "failed" : "completed") : "running",
            completedScenarios: completed, failedScenarios: failed,
          });
        }
      }

      if (update.type === "complete" || update.type === "error") {
        if (selectProgress(storeApi.getState() as any).running === 0) {
          eventSource.close();
          // Auto-fetch full data
          (async () => { try {
            const fullRun = await client.makeRequest(`/api/eval/runs/${newRunId}` as "/api/config");
            const d = fullRun as any;
            if (d?.scenario_runs) {
              const fullSRs = d.scenario_runs.map((s: any) => ({
                id: s.id, scenarioName: s.scenario_name, persona: s.persona || null, status: s.status,
                startTime: s.start_time, endTime: s.end_time,
                turns: (s.turns || []).map((t: any) => ({ turn_index: t.turn_index, task_index: t.task_index, user_message: t.user_message, assistant_message: t.assistant_message, tool_calls: t.tool_calls || [], task_completed: t.task_completed, task_completed_reason: t.task_completed_reason, token_usage: t.token_usage, latency_ms: t.latency_ms, checkers: t.checkers, checker_mode: t.checker_mode })),
                tasks: (s.tasks || []).map((t: any) => ({ task_index: t.task_index, description: t.description, completed: t.completed, turns_taken: t.turns_taken, final_reason: t.final_reason })),
                responseChunks: storeApi.getState().simulationRuns.find((r) => r.id === newRunId)?.scenarioRuns.find((r) => r.id === s.id || r.scenarioName === s.scenario_name)?.responseChunks || [],
                metrics: s.metrics, error: s.error,
              }));
              storeApi.getState().actions.updateSimulationRun(newRunId, { scenarioRuns: fullSRs, status: d.status, totalTokens: d.total_tokens || 0, totalCostUsd: d.total_cost_usd || 0, overallSuccessRate: d.overall_success_rate || 0 });
            }
          } catch { /* non-critical */ } })();
        }
      }
    } catch (err) { console.error("SSE parse error:", err); }
  };
  eventSource.onerror = () => { eventSource.close(); };

  return newRunId;
}
