/**
 * Type definitions for the evaluation UI.
 */

// Scenario types
export interface TaskDetail {
  task: string;
  checkers: CheckerConfigItem[];
  checker_mode?: "all" | "any";
}

// Individual checker config - has "type" and type-specific fields
export interface CheckerConfigItem {
  type: string;
  [key: string]: unknown;
}

export interface Scenario {
  name: string;
  tasks: TaskDetail[];
}

export interface ScenarioSummary {
  name: string;
  num_tasks: number;
  group: string | null;
}

// Persona types
export interface Persona {
  name: string;
  description: string;
}

export interface PersonasListResponse {
  personas: Persona[];
  total: number;
}

export interface ScenarioFileSummary {
  filename: string;
  group: string | null;
  scenarios: ScenarioSummary[];
}

// Execution status
export type SimulationStatus =
  | "running"
  | "completed"
  | "failed"
  | "timeout"
  | "idle"
  | "queued";

// Configuration
export interface EvalConfig {
  available_scenarios: ScenarioSummary[];
  scenario_files: ScenarioFileSummary[];
  scenarios_dir: string;
}

export interface SimulationConfig {
  max_turns_scenario: number;
  max_turns_task: number | null;
  sim_user_model_name: string | null;
  checker_model_name: string | null;
  default_model: string;
  persona: string | null;
}

// Execution tracking
export interface ScenarioExecution {
  scenarioName: string;
  status: SimulationStatus;
  startTime: number | null;
  currentTurn: number;
  currentTaskIndex: number;
  currentTask: string | null;
  turns: TurnUpdate[];
  responseChunks: ResponseChunk[];
  error: string | null;
}

export interface CheckerResultItem {
  type: string;
  completed: boolean;
  reason: string;
}

export interface TurnUpdate {
  turn_index: number;
  task_index: number;
  user_message: string;
  assistant_message: string;
  tool_calls: ToolCall[];
  task_completed: boolean;
  task_completed_reason: string;
  checkers?: CheckerResultItem[];
  checker_mode?: "all" | "any";
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
  result: unknown;
}

// Progress updates from SSE
export type ProgressUpdate =
  | StatusProgressUpdate
  | TurnProgressUpdate
  | TaskCompleteUpdate
  | CompletionUpdate
  | ErrorUpdate
  | ResponseChunkUpdate;

export interface StatusProgressUpdate {
  type: "status";
  run_id: string;
  scenario_run_id: string;
  scenario_name: string;
  persona?: string | null;
  status: SimulationStatus;
  current_turn: number | null;
  current_task_index: number | null;
  current_task: string | null;
}

export interface TurnProgressUpdate {
  type: "turn";
  run_id: string;
  scenario_run_id: string;
  scenario_name: string;
  persona?: string | null;
  turn_index: number;
  task_index: number;
  user_message: string;
  assistant_message: string;
  tool_calls: ToolCall[];
  task_completed: boolean;
  task_completed_reason: string;
  checkers?: CheckerResultItem[];
  checker_mode?: "all" | "any";
}

export interface TaskCompleteUpdate {
  type: "task_complete";
  run_id: string;
  scenario_run_id: string;
  scenario_name: string;
  persona?: string | null;
  task_index: number;
  task_description: string;
  turns_taken: number;
  reason: string;
}

export interface CompletionUpdate {
  type: "complete";
  run_id: string;
  scenario_run_id: string;
  scenario_name: string;
  persona?: string | null;
  result_id: string;
  status: SimulationStatus;
  success_rate: number;
  total_turns: number;
  total_tasks: number;
  tasks_completed: number;
}

export interface ErrorUpdate {
  type: "error";
  run_id: string;
  scenario_run_id: string;
  scenario_name: string;
  persona?: string | null;
  error: string;
}

export interface ResponseChunkUpdate {
  type: "response_chunk";
  run_id: string;
  scenario_run_id: string;
  scenario_name: string;
  persona?: string | null;
  turn_index: number;
  task_index: number;
  chunk_type: string;
  chunk_data: Record<string, unknown>;
}

// Stored response chunk with additional client-side metadata
export interface ResponseChunk {
  turn_index: number;
  task_index: number;
  chunk_index: number;
  chunk_type: string;
  chunk_data: Record<string, unknown>;
  timestamp: number;
}

// Results
export interface ResultSummary {
  result_id: string;
  scenario_name: string;
  timestamp: string;
  status: SimulationStatus;
  tasks_completed: number;
  total_tasks: number;
  success_rate: number;
  total_turns: number;
  total_tokens: number;
  total_cost_usd: number;
}

export interface SimulationResult {
  scenario_name: string;
  start_time: string;
  end_time: string | null;
  status: SimulationStatus;
  agent_model: string | null;
  simulated_user_model: string | null;
  checker_model: string | null;
  persona: string | null;
  error: string | null;
  turns: TurnResult[];
  tasks: TaskResult[];
  metrics: ConversationMetrics | null;
}

export interface TurnResult {
  turn_index: number;
  task_index: number;
  user_message: string;
  assistant_message: string;
  tool_calls: ToolCall[];
  task_completed: boolean;
  task_completed_reason: string;
  token_usage: {
    total: number;
    prompt: number;
    completion: number;
  } | null;
  latency_ms: number | null;
  checkers?: CheckerResultItem[];
  checker_mode?: "all" | "any";
}

export interface TaskResult {
  task_index: number;
  description: string;
  completed: boolean;
  turns_taken: number;
  final_reason: string;
  checkers?: CheckerConfigItem[];
  checker_mode?: "all" | "any";
}

export interface ConversationMetrics {
  // Core metrics (always present)
  total_turns: number;
  total_tasks: number;
  tasks_completed: number;
  success_rate: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_usd: number;

  // Additional metrics from collectors (dynamic)
  [key: string]: unknown;
}

// UI State
export type ViewMode = "conversation" | "summary" | "responses";

// Navigation modes for the eval dashboard
export type EvalView = "scenarios" | "scenario-detail" | "runner";

// Run history entry - represents a single execution run
export interface RunHistoryEntry {
  runId: string;
  scenarioName: string;
  timestamp: number;
  status: SimulationStatus;
  execution: ScenarioExecution;
}

export interface ExecutionProgress {
  total: number;
  completed: number;
  failed: number;
  running: number;
  percentage: number;
}

// Batch run types - a SimulationRun contains multiple ScenarioRuns
export interface SimulationRun {
  id: string;
  timestamp: string;
  version: string;
  status: SimulationStatus;
  scenarioRuns: ScenarioRun[];
  config: SimulationConfig;
  // Group info - set when all scenarios belong to the same group
  group: string | null;
  // Aggregated metrics
  totalScenarios: number;
  completedScenarios: number;
  failedScenarios: number;
  totalTokens: number;
  totalCostUsd: number;
  overallSuccessRate: number;
}

export interface ScenarioRun {
  id: string; // Unique ID for this scenario run (scenario + persona + run_id)
  scenarioName: string;
  persona: string | null;
  status: SimulationStatus;
  startTime: string;
  endTime: string | null;
  turns: TurnResult[];
  tasks: TaskResult[];
  metrics: ConversationMetrics | null;
  error: string | null;
  responseChunks?: ResponseChunk[]; // Response chunks from live streaming
}
