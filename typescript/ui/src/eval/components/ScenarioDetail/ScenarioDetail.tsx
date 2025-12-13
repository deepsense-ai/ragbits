import { useCallback, useState } from "react";
import {
  Button,
  Card,
  CardBody,
  Input,
  Textarea,
  Chip,
  Divider,
  Tooltip,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { TaskPersonaTestModal } from "./TaskPersonaTestModal";
import type { TaskDetail } from "../../types";

export function ScenarioDetail() {
  const storeApi = useEvalStoreApi();
  const selectedScenarioName = useEvalStore((s) => s.selectedScenarioName);
  const scenarios = useEvalStore((s) => s.scenarios);
  const runHistoryMap = useEvalStore((s) => s.runHistory);

  // Derive values from stable selectors
  const scenario = selectedScenarioName ? scenarios[selectedScenarioName] : null;
  const runHistory = selectedScenarioName ? runHistoryMap[selectedScenarioName] : null;

  const [editingTaskIndex, setEditingTaskIndex] = useState<number | null>(null);
  const [editedTask, setEditedTask] = useState<TaskDetail | null>(null);
  const [testingTaskIndex, setTestingTaskIndex] = useState<number | null>(null);
  const [testingTask, setTestingTask] = useState<TaskDetail | null>(null);

  const handleBack = useCallback(() => {
    storeApi.getState().actions.navigateBack();
  }, [storeApi]);

  const handleRunScenario = useCallback(() => {
    if (selectedScenarioName) {
      storeApi.getState().actions.navigateToRunner(selectedScenarioName);
    }
  }, [storeApi, selectedScenarioName]);

  const handleEditTask = (index: number, task: TaskDetail) => {
    setEditingTaskIndex(index);
    setEditedTask({ ...task });
  };

  const handleSaveTask = () => {
    if (editingTaskIndex !== null && editedTask && selectedScenarioName) {
      storeApi.getState().actions.updateScenarioTask(
        selectedScenarioName,
        editingTaskIndex,
        editedTask
      );
      setEditingTaskIndex(null);
      setEditedTask(null);
    }
  };

  const handleCancelEdit = () => {
    setEditingTaskIndex(null);
    setEditedTask(null);
  };

  const handleTestWithPersona = (index: number, task: TaskDetail) => {
    setTestingTaskIndex(index);
    setTestingTask(task);
  };

  const handleCloseTestModal = () => {
    setTestingTaskIndex(null);
    setTestingTask(null);
  };

  if (!selectedScenarioName || !scenario) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-foreground-500">No scenario selected</p>
      </div>
    );
  }

  const lastRun = runHistory?.[0];

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-divider px-6 py-4">
        <div className="flex items-center gap-4">
          <Button
            isIconOnly
            variant="light"
            onPress={handleBack}
            aria-label="Go back"
          >
            <Icon icon="heroicons:arrow-left" className="text-xl" />
          </Button>
          <div className="flex-1">
            <h1 className="text-xl font-semibold text-foreground">
              {scenario.name}
            </h1>
            <p className="text-sm text-foreground-500">
              {scenario.tasks.length} task{scenario.tasks.length !== 1 ? "s" : ""}
            </p>
          </div>
          <Button
            color="primary"
            startContent={<Icon icon="heroicons:play" />}
            onPress={handleRunScenario}
          >
            Run Scenario
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Quick Stats */}
          <div className="flex gap-4">
            <Card className="flex-1">
              <CardBody className="flex flex-row items-center gap-3 p-4">
                <div className="rounded-lg bg-primary-100 dark:bg-primary-900/30 p-2">
                  <Icon icon="heroicons:clipboard-document-list" className="text-xl text-primary" />
                </div>
                <div>
                  <p className="text-xs text-foreground-500">Tasks</p>
                  <p className="text-lg font-semibold">{scenario.tasks.length}</p>
                </div>
              </CardBody>
            </Card>
            <Card className="flex-1">
              <CardBody className="flex flex-row items-center gap-3 p-4">
                <div className="rounded-lg bg-success-100 dark:bg-success-900/30 p-2">
                  <Icon icon="heroicons:clock" className="text-xl text-success" />
                </div>
                <div>
                  <p className="text-xs text-foreground-500">Last Run</p>
                  <p className="text-lg font-semibold">
                    {lastRun
                      ? new Date(lastRun.timestamp).toLocaleDateString()
                      : "Never"}
                  </p>
                </div>
              </CardBody>
            </Card>
            <Card className="flex-1">
              <CardBody className="flex flex-row items-center gap-3 p-4">
                <div className="rounded-lg bg-warning-100 dark:bg-warning-900/30 p-2">
                  <Icon icon="heroicons:chart-bar" className="text-xl text-warning" />
                </div>
                <div>
                  <p className="text-xs text-foreground-500">Total Runs</p>
                  <p className="text-lg font-semibold">{runHistory?.length ?? 0}</p>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Tasks Section */}
          <div>
            <h2 className="text-lg font-semibold mb-4">Tasks</h2>
            <div className="space-y-4">
              {scenario.tasks.map((task, index) => (
                <Card key={index}>
                  <CardBody className="p-4">
                    {editingTaskIndex === index ? (
                      // Edit Mode
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-foreground-500">
                            Task {index + 1}
                          </span>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="flat"
                              onPress={handleCancelEdit}
                            >
                              Cancel
                            </Button>
                            <Button
                              size="sm"
                              color="primary"
                              onPress={handleSaveTask}
                            >
                              Save
                            </Button>
                          </div>
                        </div>
                        <Textarea
                          label="Task Description"
                          value={editedTask?.task ?? ""}
                          onValueChange={(value) =>
                            setEditedTask((prev) =>
                              prev ? { ...prev, task: value } : null
                            )
                          }
                          minRows={2}
                        />
                        <Input
                          label="Expected Result"
                          value={editedTask?.expected_result ?? ""}
                          onValueChange={(value) =>
                            setEditedTask((prev) =>
                              prev ? { ...prev, expected_result: value } : null
                            )
                          }
                        />
                        <Input
                          label="Expected Tools (comma-separated)"
                          value={editedTask?.expected_tools?.join(", ") ?? ""}
                          onValueChange={(value) =>
                            setEditedTask((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    expected_tools: value
                                      ? value.split(",").map((t) => t.trim())
                                      : null,
                                  }
                                : null
                            )
                          }
                        />
                      </div>
                    ) : (
                      // View Mode
                      <div>
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Chip size="sm" variant="flat" color="primary">
                                Task {index + 1}
                              </Chip>
                            </div>
                            <p className="text-foreground">{task.task}</p>
                          </div>
                          <div className="flex items-center gap-1">
                            <Tooltip content="Test with Persona">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                onPress={() => handleTestWithPersona(index, task)}
                                aria-label="Test with persona"
                              >
                                <Icon icon="heroicons:user-circle" />
                              </Button>
                            </Tooltip>
                            <Tooltip content="Edit task">
                              <Button
                                isIconOnly
                                size="sm"
                                variant="light"
                                onPress={() => handleEditTask(index, task)}
                                aria-label="Edit task"
                              >
                                <Icon icon="heroicons:pencil" />
                              </Button>
                            </Tooltip>
                          </div>
                        </div>
                        <Divider className="my-3" />
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-foreground-500 mb-1">Expected Result</p>
                            <p className="text-foreground">{task.expected_result}</p>
                          </div>
                          <div>
                            <p className="text-foreground-500 mb-1">Expected Tools</p>
                            {task.expected_tools ? (
                              <div className="flex flex-wrap gap-1">
                                {task.expected_tools.map((tool, i) => (
                                  <Chip key={i} size="sm" variant="flat">
                                    {tool}
                                  </Chip>
                                ))}
                              </div>
                            ) : (
                              <p className="text-foreground-400 italic">None specified</p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </CardBody>
                </Card>
              ))}
            </div>
          </div>

          {/* Run History Section */}
          {runHistory && runHistory.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Recent Runs</h2>
              <div className="space-y-2">
                {runHistory.slice(0, 5).map((run) => (
                  <Card
                    key={run.runId}
                    isPressable
                    onPress={() => {
                      storeApi.getState().actions.selectRun(run.runId);
                      storeApi.getState().actions.navigateToRunner(run.scenarioName);
                    }}
                  >
                    <CardBody className="flex flex-row items-center justify-between p-3">
                      <div className="flex items-center gap-3">
                        <Chip
                          size="sm"
                          color={
                            run.status === "completed"
                              ? "success"
                              : run.status === "failed"
                              ? "danger"
                              : run.status === "timeout"
                              ? "warning"
                              : "default"
                          }
                          variant="flat"
                        >
                          {run.status}
                        </Chip>
                        <span className="text-sm text-foreground">
                          {new Date(run.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-foreground-500">
                        <span>{run.execution.turns.length} turns</span>
                        <Icon icon="heroicons:chevron-right" />
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Task Persona Test Modal */}
      <TaskPersonaTestModal
        isOpen={testingTaskIndex !== null}
        onClose={handleCloseTestModal}
        task={testingTask}
        taskIndex={testingTaskIndex ?? 0}
        scenarioName={selectedScenarioName}
      />
    </div>
  );
}
