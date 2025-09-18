"""Todo list management tool for agents with workflow enforcement."""

import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal


class TaskStatus(str, Enum):
    """Task status options."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Structured task representation."""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    order: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "order": self.order,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "summary": self.summary
        }


@dataclass
class TodoSession:
    """Todo session with workflow enforcement."""

    session_id: str
    tasks: dict[str, Task] = field(default_factory=dict)
    current_task_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def get_current_task(self) -> Task | None:
        """Get the current task that should be worked on."""
        ordered_tasks = self.get_ordered_tasks()
        if self.current_task_index < len(ordered_tasks):
            return ordered_tasks[self.current_task_index]
        return None

    def get_ordered_tasks(self) -> list[Task]:
        """Get tasks in execution order."""
        return sorted(self.tasks.values(), key=lambda t: t.order)

    def can_start_task(self, task_id: str) -> tuple[bool, str]:
        """Check if a task can be started (workflow enforcement)."""
        task = self.tasks.get(task_id)
        if not task:
            return False, f"Task {task_id} not found"

        current_task = self.get_current_task()
        if current_task and current_task.id != task_id:
            return False, f"Must complete current task '{current_task.description}' first"

        if task.status != TaskStatus.PENDING:
            return False, f"Task is already {task.status.value}"

        return True, "OK"

    def advance_to_next_task(self):
        """Move to next pending task."""
        self.current_task_index += 1


# Thread-safe storage
_storage_lock = threading.Lock()
_SESSIONS: dict[str, TodoSession] = {}

def _get_or_create_session(session_id: str | None = None) -> str:
    """Get existing session or auto-find active session."""
    if session_id:
        if session_id in _SESSIONS:
            return session_id
        else:
            raise ValueError(f"Session {session_id} not found")

    # No session_id provided - try to find active session
    if len(_SESSIONS) == 1:
        # Only one session exists, use it
        return list(_SESSIONS.keys())[0]
    elif len(_SESSIONS) == 0:
        raise ValueError("No active sessions. Create a todo list first.")
    else:
        raise ValueError(f"Multiple sessions exist ({len(_SESSIONS)}). Please specify session_id.")


def todo_manager(
    action: Literal["create", "update", "get", "get_current", "complete_with_summary", "get_final_summary"],
    session_id: str | None = None,
    tasks: list[str] | None = None,
    task_id: str | None = None,
    status: Literal["pending", "in_progress", "completed", "cancelled"] | None = None,
    summary: str | None = None,
) -> dict[str, Any]:
    """
    Enhanced todo manager with workflow enforcement.

    Args:
        action: Action to perform - "create", "update", "get", "get_current", "complete_with_summary", "get_final_summary"
        session_id: Session identifier (auto-generated for create if None)
        tasks: List of task descriptions (required for "create" action)
        task_id: Task identifier (required for "update" and "complete_with_summary")
        status: New status (required for "update" action)
        summary: Task completion summary (required for "complete_with_summary")

    Returns:
        Dictionary with action results

    Examples:
        # Create a structured todo list
        todo_manager(action="create", tasks=["Task 1", "Task 2", "Task 3"])

        # Get the current task that should be worked on
        todo_manager(action="get_current", session_id="session123")

        # Start working on current task
        todo_manager(action="update", session_id="session123", task_id="task456", status="in_progress")

        # Complete task with summary (enforces workflow)
        todo_manager(action="complete_with_summary", session_id="session123", task_id="task456", summary="Completed analysis of requirements")

        # Get full progress
        todo_manager(action="get", session_id="session123")
    """
    with _storage_lock:
        if action == "create":
            if not tasks or len(tasks) == 0:
                raise ValueError("'tasks' parameter is required and must not be empty")
            if len(tasks) > 10:
                raise ValueError("Maximum 10 tasks allowed per session")

            session_id = session_id or str(uuid.uuid4())

            # Create new session
            session = TodoSession(session_id=session_id)

            # Create tasks with validation
            for i, description in enumerate(tasks):
                if not description or not description.strip():
                    raise ValueError(f"Task {i+1} description cannot be empty")

                task = Task(
                    id=str(uuid.uuid4()),
                    description=description.strip(),
                    order=i
                )
                session.tasks[task.id] = task

            _SESSIONS[session_id] = session

            return {
                "action": "create",
                "session_id": session_id,
                "tasks": [task.to_dict() for task in session.get_ordered_tasks()],
                "total_count": len(session.tasks),
                "current_task": session.get_current_task().to_dict() if session.get_current_task() else None,
                "message": f"Created {len(tasks)} tasks. Use 'get_current' to see what task to work on first."
            }

        elif action == "get_current":
            session_id = _get_or_create_session(session_id)

            session = _SESSIONS[session_id]
            current_task = session.get_current_task()

            if not current_task:
                completed_count = sum(1 for t in session.tasks.values() if t.status == TaskStatus.COMPLETED)
                completed_tasks = [t for t in session.get_ordered_tasks() if t.status == TaskStatus.COMPLETED]

                # Aggregate all task summaries for final output
                final_summary = ""
                if completed_tasks:
                    final_summary = "\n\n".join([
                        f"**{i+1}. {task.description}**: {task.summary}"
                        for i, task in enumerate(completed_tasks)
                        if task.summary
                    ])

                return {
                    "action": "get_current",
                    "session_id": session_id,
                    "current_task": None,
                    "message": f"All tasks completed! ({completed_count}/{len(session.tasks)})",
                    "all_completed": True,
                    "final_summary": final_summary,
                    "completed_tasks": [task.to_dict() for task in completed_tasks]
                }

            return {
                "action": "get_current",
                "session_id": session_id,
                "current_task": current_task.to_dict(),
                "progress": f"{session.current_task_index + 1}/{len(session.tasks)}",
                "message": f"Current task: '{current_task.description}'. Mark as 'in_progress' to start working."
            }

        elif action == "update":
            if not all([task_id, status]):
                raise ValueError("task_id and status are required for update")

            session_id = _get_or_create_session(session_id)

            session = _SESSIONS[session_id]
            task = session.tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            # Workflow enforcement
            if status == "in_progress":
                can_start, reason = session.can_start_task(task_id)
                if not can_start:
                    current = session.get_current_task()
                    raise ValueError(f"Workflow violation: {reason}. Use 'get_current' to see the correct task.")
                task.started_at = datetime.now()

            elif status == "completed":
                if task.status != TaskStatus.IN_PROGRESS:
                    raise ValueError("Task must be 'in_progress' before completing. Use 'complete_with_summary' instead for proper completion.")
                task.completed_at = datetime.now()
                session.advance_to_next_task()

            task.status = TaskStatus(status)

            next_task = session.get_current_task()
            return {
                "action": "update",
                "task": task.to_dict(),
                "next_task": next_task.to_dict() if next_task else None,
                "message": f"Task '{task.description}' updated to {status}."
            }

        elif action == "complete_with_summary":
            if not all([task_id, summary]):
                raise ValueError("task_id and summary are required for complete_with_summary")

            session_id = _get_or_create_session(session_id)

            session = _SESSIONS[session_id]
            task = session.tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            if task.status != TaskStatus.IN_PROGRESS:
                raise ValueError("Task must be 'in_progress' to complete with summary. Start the task first.")

            # Complete task with summary
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.summary = summary.strip()
            session.advance_to_next_task()

            next_task = session.get_current_task()
            completed_count = sum(1 for t in session.tasks.values() if t.status == TaskStatus.COMPLETED)

            return {
                "action": "complete_with_summary",
                "completed_task": task.to_dict(),
                "next_task": next_task.to_dict() if next_task else None,
                "progress": f"{completed_count}/{len(session.tasks)}",
                "message": f"✅ Task completed: '{task.description}'. Summary: {summary[:100]}..." if len(summary) > 100 else f"✅ Task completed: '{task.description}'. Summary: {summary}",
                "all_completed": next_task is None
            }

        elif action == "get":
            session_id = _get_or_create_session(session_id)

            if not session_id:
                return {
                    "action": "get",
                    "session_id": session_id,
                    "tasks": [],
                    "summary": {"total": 0, "pending": 0, "in_progress": 0, "completed": 0, "cancelled": 0},
                    "message": "No active session found."
                }

            session = _SESSIONS[session_id]
            tasks_list = session.get_ordered_tasks()

            summary = {
                "total": len(tasks_list),
                "pending": sum(1 for t in tasks_list if t.status == TaskStatus.PENDING),
                "in_progress": sum(1 for t in tasks_list if t.status == TaskStatus.IN_PROGRESS),
                "completed": sum(1 for t in tasks_list if t.status == TaskStatus.COMPLETED),
                "cancelled": sum(1 for t in tasks_list if t.status == TaskStatus.CANCELLED),
            }

            current_task = session.get_current_task()
            return {
                "action": "get",
                "session_id": session_id,
                "tasks": [task.to_dict() for task in tasks_list],
                "summary": summary,
                "current_task": current_task.to_dict() if current_task else None,
                "progress": f"{summary['completed']}/{summary['total']}",
                "message": f"Progress: {summary['completed']}/{summary['total']} tasks completed."
            }

        elif action == "get_final_summary":
            session_id = _get_or_create_session(session_id)

            session = _SESSIONS[session_id]
            completed_tasks = [t for t in session.get_ordered_tasks() if t.status == TaskStatus.COMPLETED]

            if not completed_tasks:
                return {
                    "action": "get_final_summary",
                    "session_id": session_id,
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
                "session_id": session_id,
                "final_summary": final_summary,
                "completed_tasks": [task.to_dict() for task in completed_tasks],
                "total_completed": len(completed_tasks),
                "message": f"Final summary with {len(completed_tasks)} completed tasks."
            }

        else:
            raise ValueError(f"Unknown action: {action}. Use 'create', 'update', 'get', 'get_current', 'complete_with_summary', 'get_final_summary'")


def get_todo_instruction_tpl(
    task_range: tuple[int, int] = (3, 6),
    enforce_workflow: bool = True
) -> str:
    """Generate system prompt instructions for structured todo workflow."""
    min_tasks, max_tasks = task_range

    if enforce_workflow:
        return f"""

    ## Todo Workflow

    1. Work through each task one by one
    2. For each task: get_current → update to in_progress → do the work → complete_with_summary
    3. When all tasks are done, use get_final_summary to present the complete results

    CRITICAL: When completing tasks with summaries, provide DETAILED, COMPREHENSIVE information.

    Available actions:
    - `todo_manager(action="create", tasks=[...])`: Create {min_tasks}-{max_tasks} tasks
    - `todo_manager(action="get_current")`: Get current task (session auto-detected)
    - `todo_manager(action="update", task_id="...", status="in_progress")`: Start task
    - `todo_manager(action="complete_with_summary", task_id="...", summary="...")`: Complete with summary
    - `todo_manager(action="get_final_summary")`: Get comprehensive final summary of all completed work

    MANDATORY WORKFLOW:
    1. Create todo list first
    2. For each task: get_current → update(in_progress) → [work] → complete_with_summary
    3. System enforces sequential order
    4. When all tasks done, use get_final_summary to present the complete results

    IMPORTANT: Task summaries should be DETAILED and COMPREHENSIVE (3-5 sentences minimum).
    Include specific information, recommendations, and actionable details.

    NOTE: Session ID is auto-detected after creation. Just use the actions as shown.
    """
    else:
        return f"""

    ## Todo Management
    Create {min_tasks}-{max_tasks} tasks for complex requests and track progress systematically.
    """
