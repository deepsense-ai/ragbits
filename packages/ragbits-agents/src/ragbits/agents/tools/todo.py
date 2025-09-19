"""Todo list management tool for agents."""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Callable


class TaskStatus(str, Enum):
    """Task status options."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Task:
    """Simple task representation."""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    order: int = 0
    summary: str | None = None


@dataclass
class TodoList:
    """Simple todo list for one agent run."""
    tasks: list[Task] = field(default_factory=list)
    current_index: int = 0

    def get_current_task(self) -> Task | None:
        """Get current task to work on."""
        if self.current_index < len(self.tasks):
            return self.tasks[self.current_index]
        return None

    def advance_to_next(self):
        """Move to next task."""
        self.current_index += 1

    def create_tasks(self, task_descriptions: list[str]) -> dict[str, Any]:
        """Create tasks from descriptions."""
        if not task_descriptions:
            raise ValueError("Tasks required for create action")

        # Clear existing tasks
        self.tasks.clear()
        self.current_index = 0

        for i, desc in enumerate(task_descriptions):
            task = Task(
                id=str(uuid.uuid4()),
                description=desc.strip(),
                order=i
            )
            self.tasks.append(task)

        return {
            "action": "create",
            "tasks": [{"id": t.id, "description": t.description, "order": t.order} for t in self.tasks],
            "total_count": len(self.tasks),
            "message": f"Created {len(task_descriptions)} tasks"
        }

    def get_current(self) -> dict[str, Any]:
        """Get current task information."""
        current = self.get_current_task()
        if not current:
            return {
                "action": "get_current",
                "current_task": None,
                "all_completed": True,
                "message": "All tasks completed!"
            }

        return {
            "action": "get_current",
            "current_task": {"id": current.id, "description": current.description, "status": current.status.value},
            "progress": f"{self.current_index + 1}/{len(self.tasks)}",
            "message": f"Current task: {current.description}"
        }

    def start_current_task(self) -> dict[str, Any]:
        """Start the current task."""
        current = self.get_current_task()
        if not current:
            raise ValueError("No current task to start")

        current.status = TaskStatus.IN_PROGRESS
        return {
            "action": "start_task",
            "task": {"id": current.id, "description": current.description, "status": current.status.value},
            "message": f"Started task: {current.description}"
        }

    def complete_current_task(self, summary: str) -> dict[str, Any]:
        """Complete the current task with summary."""
        if not summary:
            raise ValueError("Summary required for complete_task")

        current = self.get_current_task()
        if not current:
            raise ValueError("No current task to complete")

        if current.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Task must be started before completing")

        current.status = TaskStatus.COMPLETED
        current.summary = summary.strip()
        self.advance_to_next()

        next_task = self.get_current_task()
        completed_count = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

        return {
            "action": "complete_task",
            "completed_task": {"id": current.id, "description": current.description, "summary": current.summary},
            "next_task": {"id": next_task.id, "description": next_task.description} if next_task else None,
            "progress": f"{completed_count}/{len(self.tasks)}",
            "all_completed": next_task is None,
            "message": f"Completed: {current.description}"
        }

    def get_final_summary(self) -> dict[str, Any]:
        """Get comprehensive final summary of all completed work."""
        completed_tasks = [t for t in self.tasks if t.status == TaskStatus.COMPLETED]

        if not completed_tasks:
            return {
                "action": "get_final_summary",
                "final_summary": "",
                "message": "No completed tasks found."
            }

        # Create comprehensive final summary
        final_content = []
        for i, task in enumerate(completed_tasks):
            if task.summary:
                final_content.append(f"**{i+1}. {task.description}**:\n{task.summary}")
            else:
                final_content.append(f"**{i+1}. {task.description}**: Completed")

        final_summary = "\n\n".join(final_content)

        return {
            "action": "get_final_summary",
            "final_summary": final_summary,
            "total_completed": len(completed_tasks),
            "message": f"Final summary with {len(completed_tasks)} completed tasks."
        }


def create_todo_manager(todo_list: TodoList) -> Callable[..., dict[str, Any]]:
    """
    Create a todo_manager function bound to a specific TodoList instance.

    This allows each agent to have its own isolated todo list.

    Args:
        todo_list: The TodoList instance to bind to

    Returns:
        A todo_manager function that operates on the provided TodoList
    """
    def todo_manager(
        action: Literal["create", "get_current", "start_task", "complete_task", "get_final_summary"],
        tasks: list[str] | None = None,
        summary: str | None = None,
    ) -> dict[str, Any]:
        """
        Todo manager bound to a specific TodoList instance.

        Actions:
        - create: Create todo list with tasks
        - get_current: Get current task to work on
        - start_task: Mark current task as in progress
        - complete_task: Complete current task with summary
        - get_final_summary: Get all completed work
        """
        if action == "create":
            return todo_list.create_tasks(tasks or [])
        elif action == "get_current":
            return todo_list.get_current()
        elif action == "start_task":
            return todo_list.start_current_task()
        elif action == "complete_task":
            return todo_list.complete_current_task(summary or "")
        elif action == "get_final_summary":
            return todo_list.get_final_summary()
        else:
            raise ValueError(f"Unknown action: {action}")

    return todo_manager


def get_todo_instruction_tpl(task_range: tuple[int, int] = (3, 5)) -> str:
    """Generate system prompt instructions for todo workflow."""
    min_tasks, max_tasks = task_range

    return f"""

    ## Todo Workflow

    Available actions:
    - `todo_manager(action="create", tasks=[...])`: Create {min_tasks}-{max_tasks} tasks
    - `todo_manager(action="get_current")`: Get current task
    - `todo_manager(action="start_task")`: Start current task
    - `todo_manager(action="complete_task", summary="...")`: Complete with detailed summary
    - `todo_manager(action="get_final_summary")`: Get comprehensive final results

    WORKFLOW:
    1. Create todo list
    2. For each task: get_current → start_task → [do work] → complete_task
    3. When done: get_final_summary

    IMPORTANT: Task summaries should be DETAILED and COMPREHENSIVE (3-5 sentences).
    Include specific information, recommendations, and actionable details.
    """