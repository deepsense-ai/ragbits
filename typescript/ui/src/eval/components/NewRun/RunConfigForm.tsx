import { useMemo, useCallback } from "react";
import { Input, Card, CardBody, Checkbox } from "@heroui/react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { isPersonaScenario } from "../../stores/evalStore";

export function RunConfigForm() {
  const storeApi = useEvalStoreApi();
  const config = useEvalStore((s) => s.config);
  const simulationConfig = useEvalStore((s) => s.simulationConfig);
  const selectedPersonas = useEvalStore((s) => s.selectedPersonas);

  // Get available persona scenarios
  const personas = useMemo(() => {
    if (!config) return [];
    return config.available_scenarios
      .filter((s) => isPersonaScenario(s.num_tasks))
      .map((s) => s.name);
  }, [config]);

  const handleConfigChange = useCallback(
    (key: string, value: string | number | null) => {
      storeApi.getState().actions.setSimulationConfig({ [key]: value });
    },
    [storeApi]
  );

  const handleNumberChange = useCallback(
    (key: string, value: string) => {
      const numValue = value === "" ? null : parseInt(value, 10);
      if (value === "" || (!isNaN(numValue as number) && (numValue as number) > 0)) {
        handleConfigChange(key, numValue);
      }
    },
    [handleConfigChange]
  );

  const handleTogglePersona = useCallback(
    (name: string) => {
      storeApi.getState().actions.togglePersonaForRun(name);
    },
    [storeApi]
  );

  const handleSelectAllPersonas = useCallback(() => {
    storeApi.getState().actions.selectPersonasForRun(personas);
  }, [storeApi, personas]);

  const handleClearAllPersonas = useCallback(() => {
    storeApi.getState().actions.clearPersonasForRun();
  }, [storeApi]);

  const allPersonasSelected =
    personas.length > 0 &&
    personas.every((name) => selectedPersonas.includes(name));
  const somePersonasSelected =
    selectedPersonas.length > 0 && !allPersonasSelected;

  return (
    <div className="flex flex-col gap-6">
      {/* LLM Models Section */}
      <Card>
        <CardBody className="gap-4">
          <h4 className="text-sm font-semibold text-foreground">LLM Models</h4>
          <Input
            label="Default Model"
            placeholder="e.g., gpt-4o-mini"
            size="sm"
            value={simulationConfig.default_model || ""}
            onValueChange={(value) =>
              handleConfigChange("default_model", value || "gpt-4o-mini")
            }
            description="Model for the agent under test"
          />
          <Input
            label="Simulated User Model"
            placeholder="Uses default if empty"
            size="sm"
            value={simulationConfig.sim_user_model_name || ""}
            onValueChange={(value) =>
              handleConfigChange("sim_user_model_name", value || null)
            }
            description="Model for simulating user behavior"
          />
          <Input
            label="Checker Model"
            placeholder="Uses default if empty"
            size="sm"
            value={simulationConfig.checker_model_name || ""}
            onValueChange={(value) =>
              handleConfigChange("checker_model_name", value || null)
            }
            description="Model for task completion checking"
          />
        </CardBody>
      </Card>

      {/* Limits Section */}
      <Card>
        <CardBody className="gap-4">
          <h4 className="text-sm font-semibold text-foreground">Limits</h4>
          <Input
            label="Max Turns per Scenario"
            type="number"
            min={1}
            size="sm"
            value={simulationConfig.max_turns_scenario?.toString() || ""}
            onValueChange={(value) =>
              handleNumberChange("max_turns_scenario", value)
            }
            description="Maximum conversation turns for entire scenario"
          />
          <Input
            label="Max Turns per Task"
            type="number"
            min={1}
            size="sm"
            value={simulationConfig.max_turns_task?.toString() || ""}
            onValueChange={(value) => handleNumberChange("max_turns_task", value)}
            placeholder="No limit if empty"
            description="Maximum turns allowed for each task"
          />
        </CardBody>
      </Card>

      {/* Personas Section - Multi-select */}
      {personas.length > 0 && (
        <Card>
          <CardBody className="gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-foreground">Personas</h4>
                <p className="text-xs text-foreground-500 mt-0.5">
                  Select personas for matrix runs
                </p>
              </div>
              <Checkbox
                size="sm"
                isSelected={allPersonasSelected}
                isIndeterminate={somePersonasSelected}
                onValueChange={() => {
                  if (allPersonasSelected) {
                    handleClearAllPersonas();
                  } else {
                    handleSelectAllPersonas();
                  }
                }}
              >
                <span className="text-xs">All</span>
              </Checkbox>
            </div>
            <div className="flex flex-wrap gap-2">
              {personas.map((name) => {
                const isSelected = selectedPersonas.includes(name);
                return (
                  <button
                    key={name}
                    onClick={() => handleTogglePersona(name)}
                    className={`
                      flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors
                      ${
                        isSelected
                          ? "bg-secondary-100 dark:bg-secondary-900/30 border-secondary-300 dark:border-secondary-700"
                          : "bg-content2 border-transparent hover:bg-content3"
                      }
                    `}
                  >
                    <Checkbox
                      size="sm"
                      isSelected={isSelected}
                      onValueChange={() => handleTogglePersona(name)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <span className="text-sm font-medium">{name}</span>
                  </button>
                );
              })}
            </div>
            {selectedPersonas.length > 0 && (
              <p className="text-xs text-foreground-400">
                {selectedPersonas.length} persona{selectedPersonas.length !== 1 ? "s" : ""} selected
              </p>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
