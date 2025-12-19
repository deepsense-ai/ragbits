import { useMemo, useCallback } from "react";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
  Button,
  Input,
  Select,
  SelectItem,
  Divider,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import { useEvalStore, useEvalStoreApi } from "../../stores/EvalStoreContext";
import { isPersonaScenario } from "../../stores/evalStore";

export function SimulationSettingsPopover() {
  const storeApi = useEvalStoreApi();
  const config = useEvalStore((s) => s.config);
  const simulationConfig = useEvalStore((s) => s.simulationConfig);
  const isExecuting = useEvalStore((s) => s.isExecuting);

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
    [storeApi],
  );

  const handleNumberChange = useCallback(
    (key: string, value: string) => {
      const numValue = value === "" ? null : parseInt(value, 10);
      if (value === "" || (!isNaN(numValue as number) && (numValue as number) > 0)) {
        handleConfigChange(key, numValue);
      }
    },
    [handleConfigChange],
  );

  const handleSelectChange = useCallback(
    (key: string, keys: Set<string> | "all") => {
      if (keys === "all") return;
      const value = Array.from(keys)[0] || null;
      handleConfigChange(key, value === "" ? null : value);
    },
    [handleConfigChange],
  );

  return (
    <Popover placement="bottom-end">
      <PopoverTrigger>
        <Button
          isIconOnly
          variant="light"
          isDisabled={isExecuting}
          aria-label="Simulation settings"
        >
          <Icon icon="heroicons:cog-6-tooth" className="text-lg" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="flex flex-col gap-4 p-4">
          <h3 className="text-sm font-semibold text-foreground">
            Simulation Settings
          </h3>

          {/* LLM Models Section */}
          <div className="flex flex-col gap-3">
            <p className="text-xs font-medium text-foreground-500 uppercase tracking-wide">
              LLM Models
            </p>
            <Input
              label="Default Model"
              placeholder="e.g., gpt-4o-mini"
              size="sm"
              value={simulationConfig.default_model || ""}
              onValueChange={(value) => handleConfigChange("default_model", value || "gpt-4o-mini")}
              description="Model for the agent under test"
            />
            <Input
              label="Simulated User Model"
              placeholder="Uses default if empty"
              size="sm"
              value={simulationConfig.sim_user_model_name || ""}
              onValueChange={(value) => handleConfigChange("sim_user_model_name", value || null)}
              description="Model for simulating user behavior"
            />
            <Input
              label="Checker Model"
              placeholder="Uses default if empty"
              size="sm"
              value={simulationConfig.checker_model_name || ""}
              onValueChange={(value) => handleConfigChange("checker_model_name", value || null)}
              description="Model for task completion checking"
            />
          </div>

          <Divider />

          {/* Limits Section */}
          <div className="flex flex-col gap-3">
            <p className="text-xs font-medium text-foreground-500 uppercase tracking-wide">
              Limits
            </p>
            <Input
              label="Max Turns per Scenario"
              type="number"
              min={1}
              size="sm"
              value={simulationConfig.max_turns_scenario?.toString() || ""}
              onValueChange={(value) => handleNumberChange("max_turns_scenario", value)}
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
          </div>

          {/* Personas Section */}
          {personas.length > 0 && (
            <>
              <Divider />
              <div className="flex flex-col gap-3">
                <p className="text-xs font-medium text-foreground-500 uppercase tracking-wide">
                  Persona
                </p>
                <Select
                  label="User Persona"
                  placeholder="Select a persona"
                  size="sm"
                  selectedKeys={
                    simulationConfig.persona
                      ? new Set([simulationConfig.persona])
                      : new Set()
                  }
                  onSelectionChange={(keys) => handleSelectChange("persona", keys as Set<string>)}
                  description="Persona for the simulated user"
                >
                  {personas.map((name) => (
                    <SelectItem key={name}>{name}</SelectItem>
                  ))}
                </Select>
              </div>
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
