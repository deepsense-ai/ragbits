import { Checkbox, CircularProgress } from "@heroui/react";
import { TaskTree } from "../utils/tasks";
import { Task, TaskStatus } from "@ragbits/api-client-react";
interface TodoListProps {
  tasks: Task[];
  depth?: number;
}

export default function TodoList({ tasks, depth = 0 }: TodoListProps) {
  const tasksTree = new TaskTree(tasks);

  return (
    <div className="space-y-2" data-testid={`todo-list-root-${depth}`}>
      {tasksTree.getRoots().map(({ id, description, status, children }) => {
        const inProgressIcon = (
          <CircularProgress
            size="sm"
            color="primary"
            aria-label="Task is in progress"
            className="m-0 p-0"
            classNames={{
              svg: "w-4 h-4",
            }}
          />
        );
        return (
          <div key={id} data-testid={`todo-task-${id}`}>
            <div>
              <Checkbox
                isSelected={status === TaskStatus.Completed}
                disabled
                className="block"
                icon={
                  status === TaskStatus.InProgress
                    ? () => inProgressIcon
                    : undefined
                }
                classNames={{
                  hiddenInput: "cursor-default",
                  wrapper:
                    status === TaskStatus.InProgress && "before:border-none",
                  base: "pointer-events-none hover:bg-transparent",
                  label: [
                    "transition-colors",
                    status === TaskStatus.Completed &&
                      "line-through text-default-400",
                    status === TaskStatus.InProgress && "text-primary italic",
                    status === TaskStatus.Pending && "text-default-900",
                  ]
                    .filter(Boolean)
                    .join(" "),
                }}
              >
                {description}
              </Checkbox>
            </div>
            {children.length > 0 && (
              <div
                style={{ marginLeft: `${(depth + 1) * 0.5}rem` }}
                data-testid={`todo-children-wrapper-${id}`}
              >
                <TodoList tasks={children} depth={depth + 1} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
