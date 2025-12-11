import { Card, CardBody, Chip, Divider, ScrollShadow } from "@heroui/react";
import { Icon } from "@iconify/react";
import { useEvalStore } from "../../stores/EvalStoreContext";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ConversationViewProps {
  scenarioName: string | null;
}

export function ConversationView({ scenarioName }: ConversationViewProps) {
  const execution = useEvalStore((s) =>
    scenarioName ? s.executions[scenarioName] : null,
  );
  const scenario = useEvalStore((s) =>
    scenarioName ? s.scenarios[scenarioName] : null,
  );

  if (!scenarioName) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <Icon
          icon="heroicons:chat-bubble-left-right"
          className="text-6xl text-foreground-300 mb-4"
        />
        <h2 className="text-lg font-medium text-foreground">
          Select a Scenario
        </h2>
        <p className="text-sm text-foreground-500 mt-2">
          Click on a scenario to view its conversation
        </p>
      </div>
    );
  }

  if (!execution || execution.turns.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-8 text-center">
        <Icon
          icon="heroicons:clock"
          className="text-6xl text-foreground-300 mb-4"
        />
        <h2 className="text-lg font-medium text-foreground">
          {execution ? "No Turns Yet" : "Not Started"}
        </h2>
        <p className="text-sm text-foreground-500 mt-2">
          {execution
            ? "Waiting for conversation turns..."
            : "Run the scenario to see the conversation"}
        </p>
      </div>
    );
  }

  return (
    <ScrollShadow className="h-full">
      <div className="p-6 space-y-4">
        {/* Scenario Info */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-foreground">
            {scenarioName}
          </h2>
          {scenario && (
            <p className="text-sm text-foreground-500">
              {scenario.tasks.length} tasks |{" "}
              {execution.turns.filter((t) => t.task_completed).length} completed
            </p>
          )}
        </div>

        {/* Conversation Turns */}
        {execution.turns.map((turn, index) => (
          <div key={index} className="space-y-3">
            {/* Task indicator if this is a new task */}
            {(index === 0 ||
              turn.task_index !== execution.turns[index - 1].task_index) && (
              <div className="flex items-center gap-2 py-2">
                <Divider className="flex-1" />
                <Chip size="sm" variant="flat" color="primary">
                  Task {turn.task_index + 1}
                  {scenario?.tasks[turn.task_index] && (
                    <span className="ml-1 opacity-70">
                      : {scenario.tasks[turn.task_index].task.slice(0, 30)}...
                    </span>
                  )}
                </Chip>
                <Divider className="flex-1" />
              </div>
            )}

            {/* User Message */}
            <Card className="ml-8 bg-primary-50 dark:bg-primary-900/20">
              <CardBody className="p-3">
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                    <Icon icon="heroicons:user" className="text-white text-sm" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground-500 mb-1">
                      Simulated User
                    </p>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {turn.user_message}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Assistant Message */}
            <Card className="mr-8">
              <CardBody className="p-3">
                <div className="flex items-start gap-2">
                  <div className="w-6 h-6 rounded-full bg-success flex items-center justify-center flex-shrink-0">
                    <Icon icon="heroicons:cpu-chip" className="text-white text-sm" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground-500 mb-1">Assistant</p>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {turn.assistant_message}
                      </ReactMarkdown>
                    </div>

                    {/* Tool Calls */}
                    {turn.tool_calls.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs text-foreground-500">
                          Tools Used:
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {turn.tool_calls.map((tool, i) => (
                            <Chip key={i} size="sm" variant="flat">
                              {tool.name}
                            </Chip>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Task Completion Indicator */}
            {turn.task_completed && (
              <div className="flex items-center justify-center gap-2 py-2">
                <Chip
                  size="sm"
                  color="success"
                  variant="flat"
                  startContent={<Icon icon="heroicons:check" />}
                >
                  Task Completed: {turn.task_completed_reason}
                </Chip>
              </div>
            )}
          </div>
        ))}

        {/* Status indicator at the end */}
        {execution.status === "running" && (
          <div className="flex items-center justify-center gap-2 py-4">
            <Icon
              icon="heroicons:arrow-path"
              className="animate-spin text-primary"
            />
            <span className="text-sm text-foreground-500">
              Processing turn {execution.currentTurn + 1}...
            </span>
          </div>
        )}

        {execution.status === "completed" && (
          <div className="flex items-center justify-center gap-2 py-4">
            <Chip color="success" variant="flat" startContent={<Icon icon="heroicons:check" />}>
              Scenario Completed
            </Chip>
          </div>
        )}

        {execution.status === "failed" && (
          <div className="flex flex-col items-center justify-center gap-2 py-4">
            <Chip color="danger" variant="flat" startContent={<Icon icon="heroicons:x-mark" />}>
              Scenario Failed
            </Chip>
            {execution.error && (
              <p className="text-sm text-danger">{execution.error}</p>
            )}
          </div>
        )}
      </div>
    </ScrollShadow>
  );
}
