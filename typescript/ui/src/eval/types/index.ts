/**
 * Type definitions for the evaluation UI.
 */

// Scenario types
export interface TaskDetail {
  task: string;
  expected_result: string;
  expected_tools: string[] | null;
}

export interface Scenario {
  name: string;
  tasks: TaskDetail[];
}

export interface ScenarioSummary {
  name: string;
  num_tasks: number;
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
  scenarios_dir: string;
}

export interface SimulationConfig {
  max_turns_scenario: number;
  max_turns_task: number | null;
  sim_user_model_name: string | null;
  checker_model_name: string | null;
  default_model: string;
  personality: string | null;
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
  error: string | null;
}

export interface TurnUpdate {
  turn_index: number;
  task_index: number;
  user_message: string;
  assistant_message: string;
  tool_calls: ToolCall[];
  task_completed: boolean;
  task_completed_reason: string;
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
  | ErrorUpdate;

export interface StatusProgressUpdate {
  type: "status";
  run_id: string;
  scenario_name: string;
  status: SimulationStatus;
  current_turn: number | null;
  current_task_index: number | null;
  current_task: string | null;
}

export interface TurnProgressUpdate {
  type: "turn";
  run_id: string;
  scenario_name: string;
  turn_index: number;
  task_index: number;
  user_message: string;
  assistant_message: string;
  tool_calls: ToolCall[];
  task_completed: boolean;
  task_completed_reason: string;
}

export interface TaskCompleteUpdate {
  type: "task_complete";
  run_id: string;
  scenario_name: string;
  task_index: number;
  task_description: string;
  turns_taken: number;
  reason: string;
}

export interface CompletionUpdate {
  type: "complete";
  run_id: string;
  scenario_name: string;
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
  scenario_name: string;
  error: string;
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
  personality: string | null;
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
}

export interface TaskResult {
  task_index: number;
  description: string;
  expected_result: string | null;
  completed: boolean;
  turns_taken: number;
  final_reason: string;
}

export interface ConversationMetrics {
  total_turns: number;
  total_tasks: number;
  tasks_completed: number;
  success_rate: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_cost_usd: number;
  deepeval_scores: Record<string, number>;
  custom: Record<string, unknown>;
}

// UI State
export type ViewMode = "conversation" | "summary";

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
