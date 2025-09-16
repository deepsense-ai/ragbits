"""Clean TodoAgent implementation - extends Agent directly."""

import uuid
from collections.abc import Callable
from enum import Enum
from typing import Generic, Literal

from ragbits.agents._main import Agent, AgentOptions
from ragbits.agents.mcp.server import MCPServer
from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.core.prompt.base import ChatFormat
from ragbits.core.prompt.prompt import Prompt, PromptInputT, PromptOutputT


class TaskStatus(str, Enum):
    """Task status options."""

    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    DONE = "done"


class Task:
    """Simple task representation with UUID."""

    def __init__(self, description: str, task_id: str | None = None):
        self.id = task_id or str(uuid.uuid4())
        self.description = description
        self.status = TaskStatus.PENDING

    def __repr__(self) -> str:
        return f"Task(id={self.id[:8]}..., description='{self.description}', status={self.status.value})"


class TodoAgent(
    Agent[LLMClientOptionsT, PromptInputT, PromptOutputT], Generic[LLMClientOptionsT, PromptInputT, PromptOutputT]
):
    """Agent with clean, simple todo functionality."""

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        prompt: str | type[Prompt[PromptInputT, PromptOutputT]] | Prompt[PromptInputT, PromptOutputT] | None = None,
        *,
        history: ChatFormat | None = None,
        keep_history: bool = False,
        tools: list[Callable] | None = None,
        mcp_servers: list[MCPServer] | None = None,
        default_options: AgentOptions[LLMClientOptionsT] | None = None,
    ) -> None:
        """Initialize TodoAgent - just like regular Agent but with todo capabilities."""
        super().__init__(
            llm=llm,
            prompt=prompt,
            history=history,
            keep_history=keep_history,
            tools=tools,
            mcp_servers=mcp_servers,
            default_options=default_options,
        )

        # Simple todo storage - just a list of tasks
        self.tasks: list[Task] = []

    def create_todo_list(self, tasks: dict[int, str] | list[str]) -> list[Task]:
        """
        Create todo list from tasks.

        Args:
            tasks: Either dict {1: "task1", 2: "task2"} or list ["task1", "task2"]

        Returns:
            List of created Task objects
        """
        self.tasks.clear()

        task_descriptions = list(tasks.values()) if isinstance(tasks, dict) else tasks
        for description in task_descriptions:
            task = Task(description)
            self.tasks.append(task)

        return self.tasks.copy()

    def add_task(self, description: str) -> Task:
        """Add a single task."""
        task = Task(description)
        self.tasks.append(task)
        return task

    def mark_task(self, task_id: str | int, status: Literal["pending", "in-progress", "done"]) -> Task:
        """
        Mark task status by ID.

        Args:
            task_id: Task ID (string UUID) or index (int)
            status: New status

        Returns:
            Updated task
        """
        task = self._find_task(task_id)
        task.status = TaskStatus(status)
        return task

    def get_task(self, task_id: str | int) -> Task:
        """Get task by ID or index."""
        return self._find_task(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get all tasks with specific status."""
        return [task for task in self.tasks if task.status == status]

    @property
    def pending_tasks(self) -> list[Task]:
        """Get pending tasks."""
        return self.get_tasks_by_status(TaskStatus.PENDING)

    @property
    def in_progress_tasks(self) -> list[Task]:
        """Get in-progress tasks."""
        return self.get_tasks_by_status(TaskStatus.IN_PROGRESS)

    @property
    def done_tasks(self) -> list[Task]:
        """Get completed tasks."""
        return self.get_tasks_by_status(TaskStatus.DONE)

    def _find_task(self, task_id: str | int) -> Task:
        """Find task by ID or index."""
        if isinstance(task_id, int):
            # Use as index
            if 0 <= task_id < len(self.tasks):
                return self.tasks[task_id]
            else:
                raise ValueError(f"Task index {task_id} out of range")

        # Use as UUID string
        for task in self.tasks:
            if task.id == task_id or task.id.startswith(str(task_id)):
                return task

        raise ValueError(f"Task {task_id} not found")

    def __repr__(self) -> str:
        total = len(self.tasks)
        pending = len(self.pending_tasks)
        in_progress = len(self.in_progress_tasks)
        done = len(self.done_tasks)
        return f"TodoAgent(tasks={total}, pending={pending}, in_progress={in_progress}, done={done})"
