import { Card, CardBody, Chip, Skeleton, Checkbox } from "@heroui/react";
import { Icon } from "@iconify/react";
import type { Scenario, ScenarioExecution, SimulationStatus } from "../../types";
import { cn } from "@heroui/react";

interface ScenarioCardProps {
  name: string;
  scenario: Scenario | undefined;
  execution: ScenarioExecution | undefined;
  isSelected: boolean;
  isSelectedForRun: boolean;
  onSelect: () => void;
  onToggleForRun?: () => void;
  isRunnable?: boolean;
}

const STATUS_CONFIG: Record<
  SimulationStatus,
  { color: "default" | "primary" | "success" | "warning" | "danger"; icon: string; label: string }
> = {
  idle: { color: "default", icon: "heroicons:minus", label: "Idle" },
  queued: { color: "primary", icon: "heroicons:clock", label: "Queued" },
  running: { color: "primary", icon: "heroicons:arrow-path", label: "Running" },
  completed: { color: "success", icon: "heroicons:check", label: "Completed" },
  failed: { color: "danger", icon: "heroicons:x-mark", label: "Failed" },
  timeout: { color: "warning", icon: "heroicons:clock", label: "Timeout" },
};

export function ScenarioCard({
  name,
  scenario,
  execution,
  isSelected,
  isSelectedForRun,
  onSelect,
  onToggleForRun,
  isRunnable = true,
}: ScenarioCardProps) {
  const status = execution?.status ?? "idle";
  const statusConfig = STATUS_CONFIG[status];

  return (
    <Card
      isPressable
      onPress={onSelect}
      className={cn(
        "transition-all",
        isSelected && "ring-2 ring-primary",
        isSelectedForRun && "bg-primary-50 dark:bg-primary-900/20",
      )}
    >
      <CardBody className="gap-2 p-3">
        <div className="flex items-start justify-between gap-2">
          {isRunnable && (
            <Checkbox
              size="sm"
              isSelected={isSelectedForRun}
              onValueChange={() => onToggleForRun?.()}
              onClick={(e) => e.stopPropagation()}
              className="mt-0.5"
            />
          )}
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-foreground truncate">{name}</h3>
            {scenario ? (
              <p className="text-xs text-foreground-500">
                {scenario.tasks.length} task{scenario.tasks.length !== 1 ? "s" : ""}
              </p>
            ) : (
              <Skeleton className="h-3 w-16 rounded mt-1" />
            )}
          </div>
          <Chip
            size="sm"
            color={statusConfig.color}
            variant="flat"
            startContent={
              <Icon
                icon={statusConfig.icon}
                className={cn(
                  "text-sm",
                  status === "running" && "animate-spin",
                )}
              />
            }
          >
            {statusConfig.label}
          </Chip>
        </div>

        {/* Progress indicator for running scenarios */}
        {execution && status === "running" && (
          <div className="mt-1">
            <div className="flex items-center justify-between text-xs text-foreground-500">
              <span>Turn {execution.currentTurn}</span>
              <span>Task {execution.currentTaskIndex + 1}</span>
            </div>
            {execution.currentTask && (
              <p className="text-xs text-foreground-400 truncate mt-1">
                {execution.currentTask}
              </p>
            )}
          </div>
        )}

        {/* Error message for failed scenarios */}
        {execution && status === "failed" && execution.error && (
          <p className="text-xs text-danger mt-1 line-clamp-2">
            {execution.error}
          </p>
        )}

        {/* Results summary for completed scenarios */}
        {execution && status === "completed" && (
          <div className="flex items-center gap-2 text-xs text-foreground-500 mt-1">
            <span>{execution.turns.length} turns</span>
            <span>|</span>
            <span>
              {execution.turns.filter((t) => t.task_completed).length} tasks done
            </span>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
