"""Todo list management tool for agents."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal


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


# Storage - just one todo list per agent run
_current_todo: TodoList | None = None

def todo_manager(
    action: Literal["create", "get_current", "start_task", "complete_task", "get_final_summary"],
    tasks: list[str] | None = None,
    task_id: str | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    """
    Simplified todo manager for agent runs.

    Actions:
    - create: Create todo list with tasks
    - get_current: Get current task to work on
    - start_task: Mark current task as in progress
    - complete_task: Complete current task with summary
    - get_final_summary: Get all completed work
    """
    global _current_todo

    if action == "create":
        if not tasks:
            raise ValueError("Tasks required for create action")

        _current_todo = TodoList()
        for i, desc in enumerate(tasks):
            task = Task(
                id=str(uuid.uuid4()),
                description=desc.strip(),
                order=i
            )
            _current_todo.tasks.append(task)

        return {
            "action": "create",
            "tasks": [{"id": t.id, "description": t.description, "order": t.order} for t in _current_todo.tasks],
            "total_count": len(_current_todo.tasks),
            "message": f"Created {len(tasks)} tasks"
        }

    if not _current_todo:
        raise ValueError("No todo list exists. Create one first.")

    if action == "get_current":
        current = _current_todo.get_current_task()
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
            "progress": f"{_current_todo.current_index + 1}/{len(_current_todo.tasks)}",
            "message": f"Current task: {current.description}"
        }

    elif action == "start_task":
        current = _current_todo.get_current_task()
        if not current:
            raise ValueError("No current task to start")

        current.status = TaskStatus.IN_PROGRESS
        return {
            "action": "start_task",
            "task": {"id": current.id, "description": current.description, "status": current.status.value},
            "message": f"Started task: {current.description}"
        }

    elif action == "complete_task":
        if not summary:
            raise ValueError("Summary required for complete_task")

        current = _current_todo.get_current_task()
        if not current:
            raise ValueError("No current task to complete")

        if current.status != TaskStatus.IN_PROGRESS:
            raise ValueError("Task must be started before completing")

        current.status = TaskStatus.COMPLETED
        current.summary = summary.strip()
        _current_todo.advance_to_next()

        next_task = _current_todo.get_current_task()
        completed_count = sum(1 for t in _current_todo.tasks if t.status == TaskStatus.COMPLETED)

        return {
            "action": "complete_task",
            "completed_task": {"id": current.id, "description": current.description, "summary": current.summary},
            "next_task": {"id": next_task.id, "description": next_task.description} if next_task else None,
            "progress": f"{completed_count}/{len(_current_todo.tasks)}",
            "all_completed": next_task is None,
            "message": f"Completed: {current.description}"
        }

    elif action == "get_final_summary":
        completed_tasks = [t for t in _current_todo.tasks if t.status == TaskStatus.COMPLETED]

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

        # Clean up after getting final summary
        _current_todo = None

        return {
            "action": "get_final_summary",
            "final_summary": final_summary,
            "total_completed": len(completed_tasks),
            "message": f"Final summary with {len(completed_tasks)} completed tasks."
        }

    else:
        raise ValueError(f"Unknown action: {action}")


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
