import { Checkbox, CircularProgress } from "@heroui/react";

interface Todo {
  content: string;
  status: "initial" | "in-progress" | "done";
}

const DUMMY_TODOS: Record<string, Todo> = {
  "1": {
    content: "Todo item 1",
    status: "done",
  },
  "2": {
    content: "Todo item 2",
    status: "in-progress",
  },
  "3": {
    content: "Todo item 3",
    status: "initial",
  },
  "4": {
    content: "Todo item 4",
    status: "initial",
  },
};

interface TodoListProps {
  // TODO: Remove optional, should be optional only during development
  todos?: Record<string, Todo>;
}

export default function TodoList({ todos = DUMMY_TODOS }: TodoListProps) {
  return (
    <div className="space-y-2">
      {Object.entries(todos).map(([id, todo]) => {
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
          <Checkbox
            key={id}
            isSelected={todo.status === "done"}
            disabled
            className="block"
            icon={
              todo.status === "in-progress" ? () => inProgressIcon : undefined
            }
            classNames={{
              hiddenInput: "cursor-default",
              wrapper: todo.status === "in-progress" && "before:border-none",
              base: "pointer-events-none hover:bg-transparent",
              label: [
                "transition-colors",
                todo.status === "done" && "line-through text-default-400",
                todo.status === "in-progress" && "text-primary italic",
                todo.status === "initial" && "text-default-900",
              ]
                .filter(Boolean)
                .join(" "),
            }}
          >
            {todo.content}
          </Checkbox>
        );
      })}
    </div>
  );
}
