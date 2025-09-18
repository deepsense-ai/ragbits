import { cleanup, render, screen, within } from "@testing-library/react";
import { Task, TaskStatus } from "@ragbits/api-client-react";
import TodoList from "../../src/core/components/TodoList";
import { afterEach, describe, expect, it, vi } from "vitest";

function makeTask(partial: Partial<Task>): Task {
  return {
    id: partial.id ?? "1",
    description: partial.description ?? "Test task",
    status: partial.status ?? TaskStatus.Pending,
    order: partial.order ?? 1,
    summary: partial.summary ?? null,
    parent_id: partial.parent_id ?? null,
  } as Task;
}

describe("TodoList", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders root tasks", () => {
    const tasks = [
      makeTask({ id: "1", description: "Task A" }),
      makeTask({ id: "2", description: "Task B" }),
    ];

    render(<TodoList tasks={tasks} />);

    expect(screen.getByTestId("todo-task-1")).toBeInTheDocument();
    expect(screen.getByTestId("todo-task-2")).toBeInTheDocument();

    expect(screen.getByText("Task A")).toBeInTheDocument();
    expect(screen.getByText("Task B")).toBeInTheDocument();
  });

  it("applies completed styles and checks checkbox", () => {
    const tasks = [
      makeTask({
        id: "done",
        description: "Done",
        status: TaskStatus.Completed,
      }),
    ];

    render(<TodoList tasks={tasks} />);

    const task = screen.getByTestId("todo-task-done");
    const checkbox = within(task).getByRole("checkbox");
    expect(checkbox).toBeChecked();
    expect(screen.getByText("Done")).toHaveClass("line-through");
  });

  it("shows spinner for in-progress tasks and applies italic class", () => {
    const tasks = [
      makeTask({
        id: "working",
        description: "Working",
        status: TaskStatus.InProgress,
      }),
    ];

    render(<TodoList tasks={tasks} />);

    const task = screen.getByTestId("todo-task-working");

    const spinner = within(task).getByLabelText("Task is in progress");
    expect(spinner).toBeInTheDocument();
    expect(screen.getByText("Working")).toHaveClass("italic");
  });

  it("renders nested tasks and applies margin-left on children wrapper", () => {
    const tasks = [
      makeTask({ id: "1", description: "Parent" }),
      makeTask({ id: "2", description: "Child", parent_id: "1" }),
    ];

    render(<TodoList tasks={tasks} />);

    expect(screen.getByTestId("todo-task-1")).toBeInTheDocument();
    expect(screen.getByTestId("todo-task-2")).toBeInTheDocument();
    const childrenWrapper = screen.getByTestId("todo-children-wrapper-1");
    expect(childrenWrapper).toHaveStyle("margin-left: 0.5rem");
  });

  it("orders root tasks according to `order` field", () => {
    const tasks = [
      makeTask({ id: "a", description: "A", order: 2 }),
      makeTask({ id: "b", description: "B", order: 1 }),
    ];

    render(<TodoList tasks={tasks} />);

    const root = screen.getByTestId("todo-list-root-0");
    const renderedTasks = Array.from(
      root.querySelectorAll('[data-testid^="todo-task-"]'),
    );
    const ids = renderedTasks.map((el) => el.getAttribute("data-testid"));
    expect(ids).toEqual(["todo-task-b", "todo-task-a"]);
  });

  it("orders children according to `order` field", () => {
    const tasks = [
      makeTask({ id: "parent", description: "Parent", order: 1 }),
      makeTask({
        id: "c1",
        description: "Child 1",
        order: 2,
        parent_id: "parent",
      }),
      makeTask({
        id: "c2",
        description: "Child 2",
        order: 1,
        parent_id: "parent",
      }),
    ];

    render(<TodoList tasks={tasks} />);

    const wrapper = screen.getByTestId("todo-children-wrapper-parent");
    const childTasks = Array.from(
      wrapper.querySelectorAll('[data-testid^="todo-task-"]'),
    );
    const ids = childTasks.map((el) => el.getAttribute("data-testid"));
    expect(ids).toEqual(["todo-task-c2", "todo-task-c1"]);
  });
});
