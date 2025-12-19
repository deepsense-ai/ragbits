import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Chip,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import type { SimulationRun, SimulationStatus } from "../../../types";

interface RunsTableProps {
  runs: SimulationRun[];
  groupScenarios: Map<string, string[]>; // group name -> scenario names in that group
  onViewDetails: (runId: string) => void;
  onRerun: (runId: string) => void;
}

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

function formatDate(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatCost(cost: number): string {
  if (cost < 0.01) return "<$0.01";
  return `$${cost.toFixed(2)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}k`;
  }
  return tokens.toString();
}

// Helper to get groups where ALL scenarios from that group are included in the run
function getFullGroups(
  run: SimulationRun,
  groupScenarios: Map<string, string[]>
): string[] {
  const runScenarioNames = new Set(run.scenarioRuns.map((sr) => sr.scenarioName));
  const fullGroups: string[] = [];

  for (const [groupName, scenariosInGroup] of groupScenarios) {
    // Check if ALL scenarios from this group are in the run
    const allIncluded = scenariosInGroup.every((name) => runScenarioNames.has(name));
    if (allIncluded && scenariosInGroup.length > 0) {
      fullGroups.push(groupName);
    }
  }

  return fullGroups.sort();
}

export function RunsTable({ runs, groupScenarios, onViewDetails, onRerun }: RunsTableProps) {
  return (
    <Table
      aria-label="Simulation runs"
      classNames={{
        wrapper: "shadow-none",
      }}
    >
      <TableHeader>
        <TableColumn>SCENARIOS</TableColumn>
        <TableColumn>DATE</TableColumn>
        <TableColumn>VERSION</TableColumn>
        <TableColumn>RESULTS</TableColumn>
        <TableColumn width={180}>ACTIONS</TableColumn>
      </TableHeader>
      <TableBody>
        {runs.map((run) => {
          const statusConfig = STATUS_CONFIG[run.status];
          const scenarioNames = run.scenarioRuns.map((sr) => sr.scenarioName);
          const displayScenarios =
            scenarioNames.length <= 2
              ? scenarioNames.join(", ")
              : `${scenarioNames.slice(0, 2).join(", ")} +${scenarioNames.length - 2}`;
          const fullGroups = getFullGroups(run, groupScenarios);

          return (
            <TableRow key={run.id}>
              <TableCell>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium">{displayScenarios}</span>
                    {fullGroups.map((group) => (
                      <Chip key={group} size="sm" variant="flat" color="secondary">
                        {group}
                      </Chip>
                    ))}
                  </div>
                  <p className="text-xs text-foreground-400">
                    {run.totalScenarios} scenario
                    {run.totalScenarios !== 1 ? "s" : ""}
                  </p>
                </div>
              </TableCell>
              <TableCell>
                <span className="text-foreground-500">
                  {formatDate(run.timestamp)}
                </span>
              </TableCell>
              <TableCell>
                <span className="text-foreground-500 font-mono text-sm">
                  {run.version}
                </span>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-3">
                  <Chip size="sm" color={statusConfig.color} variant="flat">
                    {statusConfig.label}
                  </Chip>
                  <div className="flex items-center gap-4 text-sm text-foreground-500">
                    <span title="Success rate">
                      {Math.round(run.overallSuccessRate * 100)}%
                    </span>
                    <span
                      title="Scenarios"
                      className="flex items-center gap-1"
                    >
                      <Icon icon="heroicons:check-circle" className="text-xs text-success" />
                      {run.completedScenarios}/{run.totalScenarios}
                    </span>
                    <span title="Tokens" className="flex items-center gap-1">
                      <Icon icon="heroicons:cpu-chip" className="text-xs" />
                      {formatTokens(run.totalTokens)}
                    </span>
                    <span title="Cost" className="flex items-center gap-1">
                      <Icon icon="heroicons:currency-dollar" className="text-xs" />
                      {formatCost(run.totalCostUsd)}
                    </span>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Dropdown>
                    <DropdownTrigger>
                      <Button
                        size="sm"
                        variant="flat"
                        endContent={<Icon icon="heroicons:chevron-down" />}
                      >
                        Details
                      </Button>
                    </DropdownTrigger>
                    <DropdownMenu aria-label="Run actions">
                      <DropdownItem
                        key="view"
                        startContent={<Icon icon="heroicons:eye" />}
                        onPress={() => onViewDetails(run.id)}
                      >
                        View details
                      </DropdownItem>
                      <DropdownItem
                        key="metrics"
                        startContent={<Icon icon="heroicons:chart-bar" />}
                        onPress={() => onViewDetails(run.id)}
                      >
                        View metrics
                      </DropdownItem>
                    </DropdownMenu>
                  </Dropdown>
                  <Button
                    size="sm"
                    variant="bordered"
                    onPress={() => onRerun(run.id)}
                    startContent={<Icon icon="heroicons:arrow-path" />}
                  >
                    Run
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
