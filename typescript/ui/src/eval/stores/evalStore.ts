import { immer } from "zustand/middleware/immer";
import { createStore } from "zustand";
import type {
  EvalConfig,
  Scenario,
  ScenarioExecution,
  SimulationConfig,
  ProgressUpdate,
  ViewMode,
  ExecutionProgress,
  ResultSummary,
  SimulationResult,
  TurnUpdate,
} from "../types";

// Helper to check if a scenario is a personality (not runnable directly)
export const isPersonalityScenario = (name: string): boolean => {
  return name.toLowerCase().startsWith("personality");
};

export interface EvalStore {
  // Configuration
  config: EvalConfig | null;
  isConfigLoading: boolean;
  configError: string | null;

  // Scenarios
  scenarios: Record<string, Scenario>;
  selectedScenarioName: string | null;
  selectedForRun: string[]; // Scenarios selected for running

  // Execution state
  executions: Record<string, ScenarioExecution>;
  currentRunId: string | null;
  isExecuting: boolean;
  simulationConfig: SimulationConfig;

  // Results
  results: ResultSummary[];
  selectedResult: SimulationResult | null;
  isResultsLoading: boolean;

  // UI state
  viewMode: ViewMode;

  // Actions
  actions: {
    // Config
    setConfig: (config: EvalConfig) => void;
    setConfigLoading: (loading: boolean) => void;
    setConfigError: (error: string | null) => void;

    // Scenarios
    setScenario: (name: string, scenario: Scenario) => void;
    selectScenario: (name: string | null) => void;
    updateScenarioTask: (
      scenarioName: string,
      taskIndex: number,
      updates: Partial<Scenario["tasks"][0]>,
    ) => void;

    // Selection for running
    toggleScenarioForRun: (name: string) => void;
    selectAllScenariosForRun: () => void;
    clearScenariosForRun: () => void;

    // Execution
    startExecution: (runId: string, scenarioNames: string[]) => void;
    handleProgressUpdate: (update: ProgressUpdate) => void;
    stopExecution: () => void;
    clearExecutions: () => void;
    setSimulationConfig: (config: Partial<SimulationConfig>) => void;

    // Results
    setResults: (results: ResultSummary[]) => void;
    setSelectedResult: (result: SimulationResult | null) => void;
    setResultsLoading: (loading: boolean) => void;
    addResult: (result: ResultSummary) => void;

    // UI
    setViewMode: (mode: ViewMode) => void;

    // Dev/Testing
    loadMockData: () => void;
  };
}

const DEFAULT_SIMULATION_CONFIG: SimulationConfig = {
  max_turns_scenario: 15,
  max_turns_task: 4,
  sim_user_model_name: null,
  checker_model_name: null,
  default_model: "gpt-4o-mini",
};

export const createEvalStore = () =>
  createStore<EvalStore>()(
    immer((set, _get) => ({
      // Initial state
      config: null,
      isConfigLoading: false,
      configError: null,
      scenarios: {},
      selectedScenarioName: null,
      selectedForRun: [],
      executions: {},
      currentRunId: null,
      isExecuting: false,
      simulationConfig: DEFAULT_SIMULATION_CONFIG,
      results: [],
      selectedResult: null,
      isResultsLoading: false,
      viewMode: "summary" as ViewMode,

      actions: {
        setConfig: (config) => {
          set((state) => {
            state.config = config;
            state.isConfigLoading = false;
            state.configError = null;
          });
        },

        setConfigLoading: (loading) => {
          set((state) => {
            state.isConfigLoading = loading;
          });
        },

        setConfigError: (error) => {
          set((state) => {
            state.configError = error;
            state.isConfigLoading = false;
          });
        },

        setScenario: (name, scenario) => {
          set((state) => {
            state.scenarios[name] = scenario;
          });
        },

        selectScenario: (name) => {
          set((state) => {
            state.selectedScenarioName = name;
          });
        },

        updateScenarioTask: (scenarioName, taskIndex, updates) => {
          set((state) => {
            const scenario = state.scenarios[scenarioName];
            if (scenario && scenario.tasks[taskIndex]) {
              Object.assign(scenario.tasks[taskIndex], updates);
            }
          });
        },

        toggleScenarioForRun: (name) => {
          set((state) => {
            const index = state.selectedForRun.indexOf(name);
            if (index === -1) {
              state.selectedForRun.push(name);
            } else {
              state.selectedForRun.splice(index, 1);
            }
          });
        },

        selectAllScenariosForRun: () => {
          set((state) => {
            if (!state.config) return;
            // Select all non-personality scenarios
            state.selectedForRun = state.config.available_scenarios
              .map((s) => s.name)
              .filter((name) => !isPersonalityScenario(name));
          });
        },

        clearScenariosForRun: () => {
          set((state) => {
            state.selectedForRun = [];
          });
        },

        startExecution: (runId, scenarioNames) => {
          set((state) => {
            state.currentRunId = runId;
            state.isExecuting = true;

            // Initialize executions for each scenario
            for (const name of scenarioNames) {
              state.executions[name] = {
                scenarioName: name,
                status: "queued",
                startTime: Date.now(),
                currentTurn: 0,
                currentTaskIndex: 0,
                currentTask: null,
                turns: [],
                error: null,
              };
            }
          });
        },

        handleProgressUpdate: (update) => {
          set((state) => {
            const execution = state.executions[update.scenario_name];
            if (!execution) return;

            switch (update.type) {
              case "status":
                execution.status = update.status;
                execution.currentTurn = update.current_turn ?? 0;
                execution.currentTaskIndex = update.current_task_index ?? 0;
                execution.currentTask = update.current_task ?? null;
                break;

              case "turn": {
                const turnUpdate: TurnUpdate = {
                  turn_index: update.turn_index,
                  task_index: update.task_index,
                  user_message: update.user_message,
                  assistant_message: update.assistant_message,
                  tool_calls: update.tool_calls,
                  task_completed: update.task_completed,
                  task_completed_reason: update.task_completed_reason,
                };
                execution.turns.push(turnUpdate);
                execution.currentTurn = update.turn_index;
                execution.currentTaskIndex = update.task_index;
                break;
              }

              case "task_complete":
                // Task completion is tracked via turn updates
                break;

              case "complete":
                execution.status = update.status;
                // Check if all executions are complete
                const allComplete = Object.values(state.executions).every(
                  (e) =>
                    e.status === "completed" ||
                    e.status === "failed" ||
                    e.status === "timeout",
                );
                if (allComplete) {
                  state.isExecuting = false;
                }
                break;

              case "error":
                execution.status = "failed";
                execution.error = update.error;
                // Check if all executions are complete
                const allDone = Object.values(state.executions).every(
                  (e) =>
                    e.status === "completed" ||
                    e.status === "failed" ||
                    e.status === "timeout",
                );
                if (allDone) {
                  state.isExecuting = false;
                }
                break;
            }
          });
        },

        stopExecution: () => {
          set((state) => {
            state.isExecuting = false;
            // Mark running executions as failed
            for (const execution of Object.values(state.executions)) {
              if (
                execution.status === "running" ||
                execution.status === "queued"
              ) {
                execution.status = "failed";
                execution.error = "Stopped by user";
              }
            }
          });
        },

        clearExecutions: () => {
          set((state) => {
            state.executions = {};
            state.currentRunId = null;
            state.isExecuting = false;
          });
        },

        setSimulationConfig: (config) => {
          set((state) => {
            Object.assign(state.simulationConfig, config);
          });
        },

        setResults: (results) => {
          set((state) => {
            state.results = results;
            state.isResultsLoading = false;
          });
        },

        setSelectedResult: (result) => {
          set((state) => {
            state.selectedResult = result;
          });
        },

        setResultsLoading: (loading) => {
          set((state) => {
            state.isResultsLoading = loading;
          });
        },

        addResult: (result) => {
          set((state) => {
            // Add to the beginning of the list
            state.results.unshift(result);
          });
        },

        setViewMode: (mode) => {
          set((state) => {
            state.viewMode = mode;
          });
        },

        loadMockData: () => {
          set((state) => {
            // Mock config
            state.config = {
              available_scenarios: [
                { name: "Scenario 1", num_tasks: 3 },
                { name: "Scenario 2", num_tasks: 2 },
                { name: "Scenario 3", num_tasks: 4 },
                { name: "Scenario 4", num_tasks: 3 },
                { name: "Scenario 5", num_tasks: 2 },
                { name: "Scenario 6", num_tasks: 5 },
                { name: "Personality 1", num_tasks: 0 },
                { name: "Personality 2", num_tasks: 0 },
                { name: "Personality 3", num_tasks: 0 },
              ],
              scenarios_dir: "/mock/scenarios",
            };
            state.isConfigLoading = false;

            // Mock scenarios
            state.scenarios = {
              "Scenario 1": {
                name: "Scenario 1",
                tasks: [
                  { task: "Search for available rooms in Krakow", expected_result: "List of rooms", expected_tools: ["search_rooms"] },
                  { task: "Filter by deluxe rooms", expected_result: "Deluxe rooms only", expected_tools: ["filter_rooms"] },
                  { task: "Book a room", expected_result: "Confirmation", expected_tools: ["book_room"] },
                ],
              },
              "Scenario 2": {
                name: "Scenario 2",
                tasks: [
                  { task: "Check weather", expected_result: "Weather info", expected_tools: ["get_weather"] },
                  { task: "Plan activities", expected_result: "Activity list", expected_tools: null },
                ],
              },
            };

            // Mock executions with conversation data
            state.executions = {
              "Scenario 1": {
                scenarioName: "Scenario 1",
                status: "completed",
                startTime: Date.now() - 60000,
                currentTurn: 3,
                currentTaskIndex: 2,
                currentTask: null,
                turns: [
                  {
                    turn_index: 0,
                    task_index: 0,
                    user_message: "Can you check for available rooms in Krakow on June 1, 2025?",
                    assistant_message: "Here are the available rooms in Kraków on June 1, 2025:\n\n1. **Grand Hotel Kraków**\n   - Room 102 (Standard): 350 PLN/night\n   - Room 202 (Deluxe): 500 PLN/night\n\n2. **Hotel Stary Kraków**\n   - Room 12 (Standard): 320 PLN/night\n   - Room 22 (Deluxe): 480 PLN/night\n\nWould you like to book any of these rooms?",
                    tool_calls: [{ name: "search_available_rooms", arguments: { city: "Krakow", date: "2025-06-01" }, result: {} }],
                    task_completed: true,
                    task_completed_reason: "Listed available rooms successfully",
                  },
                  {
                    turn_index: 1,
                    task_index: 1,
                    user_message: "Show me only the deluxe rooms please.",
                    assistant_message: "Here are the deluxe rooms available:\n\n1. **Grand Hotel Kraków - Room 202**\n   - Price: 500 PLN/night\n   - Capacity: 3 guests\n   - Amenities: WiFi, TV, AC, Balcony, City View\n\n2. **Hotel Stary Kraków - Room 22**\n   - Price: 480 PLN/night\n   - Capacity: 3 guests\n   - Amenities: WiFi, TV, AC, City View, Minibar",
                    tool_calls: [{ name: "filter_rooms", arguments: { type: "deluxe" }, result: {} }],
                    task_completed: true,
                    task_completed_reason: "Filtered to show only deluxe rooms",
                  },
                  {
                    turn_index: 2,
                    task_index: 2,
                    user_message: "I'd like to book Room 22 at Hotel Stary for John Doe.",
                    assistant_message: "Your reservation has been confirmed!\n\n**Booking Details:**\n- Guest: John Doe\n- Hotel: Hotel Stary Kraków\n- Room: 22 (Deluxe)\n- Date: June 1, 2025\n- Total: 480 PLN\n\nConfirmation number: HSK-2025-1234",
                    tool_calls: [{ name: "book_room", arguments: { hotel: "Hotel Stary", room: 22, guest: "John Doe" }, result: { confirmation: "HSK-2025-1234" } }],
                    task_completed: true,
                    task_completed_reason: "Room booked successfully",
                  },
                ],
                error: null,
              },
              "Scenario 2": {
                scenarioName: "Scenario 2",
                status: "completed",
                startTime: Date.now() - 30000,
                currentTurn: 2,
                currentTaskIndex: 1,
                currentTask: null,
                turns: [
                  {
                    turn_index: 0,
                    task_index: 0,
                    user_message: "What's the weather like in Warsaw today?",
                    assistant_message: "The weather in Warsaw today:\n\n- Temperature: 22°C\n- Conditions: Partly cloudy\n- Humidity: 65%\n- Wind: 10 km/h NW\n\nIt's a pleasant day for outdoor activities!",
                    tool_calls: [{ name: "get_weather", arguments: { city: "Warsaw" }, result: {} }],
                    task_completed: true,
                    task_completed_reason: "Weather information provided",
                  },
                  {
                    turn_index: 1,
                    task_index: 1,
                    user_message: "What activities do you recommend?",
                    assistant_message: "Based on the weather, here are some recommendations:\n\n1. Visit the Old Town and Royal Castle\n2. Walk through Łazienki Park\n3. Explore the Warsaw Uprising Museum\n4. Enjoy a riverbank cafe by the Vistula\n\nThe partly cloudy weather is perfect for sightseeing!",
                    tool_calls: [],
                    task_completed: true,
                    task_completed_reason: "Activities recommended",
                  },
                ],
                error: null,
              },
              "Scenario 3": {
                scenarioName: "Scenario 3",
                status: "timeout",
                startTime: Date.now() - 120000,
                currentTurn: 2,
                currentTaskIndex: 1,
                currentTask: "Complete task 2",
                turns: [
                  {
                    turn_index: 0,
                    task_index: 0,
                    user_message: "Start the process",
                    assistant_message: "Starting the process now...",
                    tool_calls: [],
                    task_completed: true,
                    task_completed_reason: "Process started",
                  },
                ],
                error: "Scenario timed out after 15 turns",
              },
            };

            state.selectedScenarioName = "Scenario 1";
          });
        },
      },
    })),
  );

export type EvalStoreApi = ReturnType<typeof createEvalStore>;

// Selector helpers - use these with useEvalStore
export const selectProgress = (state: EvalStore): ExecutionProgress => {
  const all = Object.values(state.executions);
  const total = all.length;
  const completed = all.filter((e) => e.status === "completed").length;
  const failed = all.filter(
    (e) => e.status === "failed" || e.status === "timeout",
  ).length;
  const running = all.filter(
    (e) => e.status === "running" || e.status === "queued",
  ).length;
  const percentage = total > 0 ? ((completed + failed) / total) * 100 : 0;

  return { total, completed, failed, running, percentage };
};

export const selectSelectedExecution = (
  state: EvalStore,
): ScenarioExecution | null => {
  if (!state.selectedScenarioName) return null;
  return state.executions[state.selectedScenarioName] ?? null;
};
