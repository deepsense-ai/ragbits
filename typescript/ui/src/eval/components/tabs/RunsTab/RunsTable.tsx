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
          // Deduplicate scenario names (a single scenario may appear multiple times
          // when the run uses a matrix of scenarios × personas)
          const uniqueScenarioNames = Array.from(
            new Set(run.scenarioRuns.map((sr) => sr.scenarioName)),
          );
          const uniquePersonas = Array.from(
            new Set(
              run.scenarioRuns
                .map((sr) => sr.persona)
                .filter((p): p is string => Boolean(p)),
            ),
          );
          const displayScenarios =
            uniqueScenarioNames.length <= 2
              ? uniqueScenarioNames.join(", ")
              : `${uniqueScenarioNames.slice(0, 2).join(", ")} +${uniqueScenarioNames.length - 2}`;
          const fullGroups = getFullGroups(run, groupScenarios);
          const visiblePersonas = uniquePersonas.slice(0, 3);
          const hiddenPersonaCount = uniquePersonas.length - visiblePersonas.length;

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
                  <div className="mt-0.5 flex items-center gap-2 flex-wrap">
                    <p className="text-xs text-foreground-400">
                      {uniqueScenarioNames.length} scenario
                      {uniqueScenarioNames.length !== 1 ? "s" : ""}
                      {uniquePersonas.length > 0 && (
                        <>
                          {" × "}
                          {uniquePersonas.length} persona
                          {uniquePersonas.length !== 1 ? "s" : ""}
                        </>
                      )}
                    </p>
                    {visiblePersonas.map((persona) => (
                      <Chip
                        key={persona}
                        size="sm"
                        variant="flat"
                        color="primary"
                        className="text-xs"
                      >
                        {persona}
                      </Chip>
                    ))}
                    {hiddenPersonaCount > 0 && (
                      <Chip
                        size="sm"
                        variant="flat"
                        color="primary"
                        className="text-xs"
                      >
                        +{hiddenPersonaCount}
                      </Chip>
                    )}
                  </div>
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
                    {(() => {
                      // Compute counts from scenarioRuns (source of truth) rather than
                      // relying on aggregate fields which can be stale from the backend
                      // list endpoint (which counts only saved result files).
                      let totalTasks = 0;
                      let tasksCompleted = 0;
                      let totalCost = 0;
                      let totalTokens = 0;
                      let completedScenarios = 0;
                      for (const sr of run.scenarioRuns) {
                        if (sr.status === "completed") completedScenarios += 1;
                        if (!sr.metrics) continue;
                        const m = sr.metrics as Record<string, unknown>;
                        totalTasks += (m.total_tasks as number) ?? 0;
                        tasksCompleted += (m.tasks_completed as number) ?? 0;
                        totalCost += ((m.estimated_usd as number) ?? (m.total_cost_usd as number) ?? 0);
                        totalTokens += ((m.total_tokens as number) ?? (m.tokens_total as number) ?? 0);
                      }
                      const totalScenarios = run.scenarioRuns.length || run.totalScenarios;
                      const rate = totalTasks > 0 ? Math.round((tasksCompleted / totalTasks) * 100) : 0;
                      const displayTokens = totalTokens > 0 ? totalTokens : run.totalTokens;
                      const displayCost = totalCost > 0 ? totalCost : run.totalCostUsd;
                      return (
                        <>
                          <span title="Task success rate">{rate}%</span>
                          <span title="Completed scenarios" className="flex items-center gap-1">
                            <Icon icon="heroicons:check-circle" className="text-xs text-success" />
                            {completedScenarios}/{totalScenarios}
                          </span>
                          {displayTokens > 0 && (
                            <span title="Total tokens" className="flex items-center gap-1">
                              <Icon icon="heroicons:cpu-chip" className="text-xs" />
                              {formatTokens(displayTokens)}
                            </span>
                          )}
                          {displayCost > 0 && (
                            <span title="Estimated cost" className="flex items-center gap-1">
                              <Icon icon="heroicons:currency-dollar" className="text-xs" />
                              {formatCost(displayCost)}
                            </span>
                          )}
                        </>
                      );
                    })()}
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
                        onPress={() => onViewDetails(`${run.id}?tab=metrics`)}
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
