import uuid
from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task in the plan."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """A single task in a plan."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None


class Plan(BaseModel):
    """A plan consisting of tasks to accomplish a goal."""

    goal: str
    tasks: list[Task] = Field(default_factory=list)
    current_index: int = 0

    @property
    def current_task(self) -> Task | None:
        """Get the current task to work on."""
        pending = [t for t in self.tasks if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)]
        return pending[0] if pending else None

    @property
    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(t.status == TaskStatus.COMPLETED for t in self.tasks)

    @property
    def completed_tasks(self) -> list[Task]:
        """Get all completed tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]

    @property
    def pending_tasks(self) -> list[Task]:
        """Get all pending tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    @property
    def last_completed_task(self) -> Task | None:
        """Get the most recently completed task."""
        completed = self.completed_tasks
        return completed[-1] if completed else None


class PlanningState:
    """
    Holds the state for planning operations.

    Use `create_planning_tools()` to get tool functions bound to this state.
    """

    def __init__(self) -> None:
        self._plan: Plan | None = None

    @property
    def plan(self) -> Plan | None:
        """Get the current plan."""
        return self._plan

    def create_plan(self, goal: str, tasks: list[str]) -> Plan:
        """Create a new plan with the given goal and tasks."""
        self._plan = Plan(
            goal=goal,
            tasks=[Task(description=desc) for desc in tasks],
        )
        return self._plan

    def clear_plan(self) -> None:
        """Clear the current plan."""
        self._plan = None


def create_planning_tools(state: PlanningState) -> list[Callable[..., Any]]:
    """
    Create planning tool functions bound to a planning state.

    Args:
        state: Planning state instance.

    Returns:
        List of tool functions that can be passed to an Agent's tools parameter.
    """

    def create_plan(goal: str, tasks: list[str]) -> str:
        """
        Create a new plan to accomplish a goal.

        Use this when you need to break down a complex request into smaller,
        manageable tasks. Each task should be specific and actionable.

        Args:
            goal: The overall goal to accomplish.
            tasks: List of task descriptions in execution order.

        Returns:
            Confirmation message with the created plan.
        """
        plan = state.create_plan(goal, tasks)
        task_list = "\n".join(f"  {i+1}. {t.description}" for i, t in enumerate(plan.tasks))
        return f"Plan created for: {goal}\n\nTasks:\n{task_list}"

    def get_current_task() -> str:
        """
        Get the current task to work on.

        Use this to see what task should be addressed next.

        Returns:
            Description of the current task, or a message if no tasks remain.
        """
        if state.plan is None:
            return "No active plan."

        if state.plan.current_task is None:
            return "All tasks completed."

        state.plan.current_task.status = TaskStatus.IN_PROGRESS

        return f"Current task: {state.plan.current_task.description}"

    def complete_task(result: str) -> str:
        """
        Mark the current task as completed with a result summary.

        Use this after finishing work on a task to record the outcome
        and move to the next task.

        Args:
            result: Summary of what was accomplished for this task.

        Returns:
            Confirmation and information about the next task.
        """
        if state.plan is None:
            return "No active plan."

        current = None
        for task in state.plan.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                current = task
                break

        if current is None:
            return "No task in progress. Use get_current_task first."

        current.status = TaskStatus.COMPLETED
        current.result = result

        if remaining := len(state.plan.pending_tasks):
            return f"Task completed: {current.description}\n\n{remaining} tasks remaining."

        return f"Task completed: {current.description}\n\nAll tasks finished."

    def add_task(description: str, position: int | None = None) -> str:
        """
        Add a new task to the plan.

        Use this when you discover additional work needed that wasn't
        in the original plan.

        Args:
            description: Description of the new task.
            position: Position to insert the task (0-indexed). If None, appends to end.

        Returns:
            Confirmation of the added task.
        """
        if state.plan is None:
            return "No active plan. Use create_plan first."

        new_task = Task(description=description)

        if position is None or position >= len(state.plan.tasks):
            state.plan.tasks.append(new_task)
            pos = len(state.plan.tasks)
        else:
            state.plan.tasks.insert(max(0, position), new_task)
            pos = position + 1

        return f"Added task at position {pos}: {description}"

    def remove_task(task_id: str) -> str:
        """
        Remove a task from the plan by its ID.

        Use this to remove tasks that are no longer needed.
        Cannot remove tasks that are already completed or in progress.

        Args:
            task_id: The ID of the task to remove.

        Returns:
            Confirmation of removal or error message.
        """
        if state.plan is None:
            return "No active plan."

        for i, task in enumerate(state.plan.tasks):
            if task.id == task_id:
                if task.status == TaskStatus.COMPLETED:
                    return f"Cannot remove completed task: {task.description}"
                if task.status == TaskStatus.IN_PROGRESS:
                    return f"Cannot remove task in progress: {task.description}"
                state.plan.tasks.pop(i)
                return f"Removed task: {task.description}"

        return f"Task not found with ID: {task_id}"

    def clear_plan() -> str:
        """
        Clear the current plan entirely.

        Use this to abandon the current plan and start fresh.

        Returns:
            Confirmation that the plan was cleared.
        """
        state.clear_plan()
        return "Plan cleared."

    return [
        create_plan,
        get_current_task,
        complete_task,
        add_task,
        remove_task,
        clear_plan,
    ]
