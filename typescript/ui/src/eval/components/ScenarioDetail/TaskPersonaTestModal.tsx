import { useState, useCallback, useMemo } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  Button,
  Select,
  SelectItem,
  Card,
  CardBody,
  Spinner,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useEvalStore } from "../../stores/EvalStoreContext";
import { isPersonaScenario } from "../../stores/evalStore";
import type { TaskDetail } from "../../types";

interface TaskPersonaTestModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: TaskDetail | null;
  taskIndex: number;
  scenarioName: string;
}

interface PersonaResponse {
  message: string;
  persona: string;
  model: string;
}

export function TaskPersonaTestModal({
  isOpen,
  onClose,
  task,
  taskIndex,
  scenarioName,
}: TaskPersonaTestModalProps) {
  const { client } = useRagbitsContext();
  const config = useEvalStore((s) => s.config);
  const simulationConfig = useEvalStore((s) => s.simulationConfig);

  const [selectedPersona, setSelectedPersona] = useState<string | null>(
    simulationConfig.persona
  );
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<PersonaResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get available personas
  const personas = useMemo(() => {
    if (!config) return [];
    return config.available_scenarios
      .filter((s) => isPersonaScenario(s.num_tasks))
      .map((s) => s.name);
  }, [config]);

  const handleTest = useCallback(async () => {
    if (!task) return;

    setIsLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`${client.getBaseUrl()}/api/eval/test-persona`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task: task.task,
          persona: selectedPersona,
          scenario_name: scenarioName,
          task_index: taskIndex,
          model: simulationConfig.sim_user_model_name || simulationConfig.default_model,
        }),
      });

      if (!res.ok) {
        throw new Error(`Failed to test persona: ${res.statusText}`);
      }

      const data = await res.json();
      setResponse({
        message: data.message,
        persona: data.persona || selectedPersona || "Default",
        model: data.model || simulationConfig.sim_user_model_name || simulationConfig.default_model,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  }, [client, task, selectedPersona, scenarioName, taskIndex, simulationConfig]);

  const handleClose = useCallback(() => {
    setResponse(null);
    setError(null);
    onClose();
  }, [onClose]);

  const handlePersonaChange = useCallback((keys: "all" | Set<React.Key>) => {
    if (keys === "all") return;
    const value = Array.from(keys)[0] as string || null;
    setSelectedPersona(value === "" ? null : value);
  }, []);

  if (!task) return null;

  return (
    <Modal isOpen={isOpen} onOpenChange={handleClose} size="2xl">
      <ModalContent>
        <ModalHeader className="flex flex-col gap-1">
          <span className="text-foreground">Test Task with Persona</span>
          <span className="text-sm font-normal text-foreground-500">
            See how a simulated user would ask this task
          </span>
        </ModalHeader>
        <ModalBody className="pb-6">
          <div className="space-y-4">
            {/* Task Info */}
            <Card className="bg-default-50">
              <CardBody className="p-4">
                <p className="text-xs text-foreground-500 mb-1">
                  Task {taskIndex + 1}
                </p>
                <p className="text-foreground">{task.task}</p>
                {task.checkers && task.checkers.length > 0 && (
                  <p className="text-sm text-foreground-500 mt-2">
                    <span className="font-medium">Checkers: </span>
                    {task.checkers.map(c => c.type).join(", ")} ({task.checker_mode || "all"})
                  </p>
                )}
              </CardBody>
            </Card>

            {/* Persona Selection */}
            <div className="flex items-end gap-3">
              <Select
                label="Persona"
                placeholder="Select a persona (optional)"
                size="sm"
                className="flex-1"
                selectedKeys={selectedPersona ? new Set([selectedPersona]) : new Set()}
                onSelectionChange={handlePersonaChange}
                description="Choose a persona for the simulated user"
              >
                {personas.map((name) => (
                  <SelectItem key={name}>{name}</SelectItem>
                ))}
              </Select>
              <Button
                color="primary"
                onPress={handleTest}
                isLoading={isLoading}
                startContent={!isLoading && <Icon icon="heroicons:play" />}
              >
                Generate
              </Button>
            </div>

            {/* Response */}
            {isLoading && (
              <div className="flex items-center justify-center py-8">
                <Spinner size="lg" />
              </div>
            )}

            {error && (
              <Card className="bg-danger-50 dark:bg-danger-900/20">
                <CardBody className="p-4">
                  <div className="flex items-start gap-2">
                    <Icon
                      icon="heroicons:exclamation-circle"
                      className="text-danger text-xl flex-shrink-0 mt-0.5"
                    />
                    <div>
                      <p className="text-sm font-medium text-danger">Error</p>
                      <p className="text-sm text-danger-600 dark:text-danger-400">
                        {error}
                      </p>
                    </div>
                  </div>
                </CardBody>
              </Card>
            )}

            {response && (
              <Card className="bg-primary-50 dark:bg-primary-900/20">
                <CardBody className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                      <Icon icon="heroicons:user" className="text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <p className="text-sm font-medium text-foreground">
                          Simulated User
                        </p>
                        {response.persona && (
                          <span className="text-xs text-foreground-500">
                            ({response.persona})
                          </span>
                        )}
                      </div>
                      <p className="text-foreground whitespace-pre-wrap">
                        {response.message}
                      </p>
                      <p className="text-xs text-foreground-400 mt-3">
                        Model: {response.model}
                      </p>
                    </div>
                  </div>
                </CardBody>
              </Card>
            )}
          </div>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
