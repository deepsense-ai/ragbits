"""Logging functionality for agent simulation scenarios."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ragbits.agents.tool import ToolCallResult
from ragbits.evaluate.agent_simulation.models import Scenario, Task


class ConversationLogger:
    """Handles logging of conversation sessions to a file."""

    def __init__(self, log_file: str | None) -> None:
        """Initialize logger with optional log file path."""
        self.log_path: Path | None = None
        if log_file:
            self.log_path = Path(log_file)
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize_session(
        self,
        scenario: Scenario,
        agent_model_name: str | None,
        sim_user_model_name: str | None,
        checker_model_name: str | None,
    ) -> None:
        """Initialize a new logging session with scenario metadata."""
        if not self.log_path:
            return

        now_warsaw = datetime.now(ZoneInfo("Europe/Warsaw"))
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Session start: {now_warsaw.isoformat()}\n")
            f.write(f"Scenario: {scenario.name}\n")
            f.write(f"Tasks: {len(scenario.tasks)}\n")
            for i, task in enumerate(scenario.tasks, 1):
                f.write(f"  Task {i}: {task.task}\n")
                f.write(f"    Expected: {task.expected_result}\n")
            f.write(f"Agent model: {agent_model_name or 'default'}\n")
            f.write(f"Simulated user model: {sim_user_model_name or 'default'}\n")
            f.write(f"Goal checker model: {checker_model_name or 'default'}\n")

    def log_turn(
        self,
        turn_idx: int,
        task: Task | None,
        user_msg: str,
        assistant_msg: str | None = None,
        tool_calls: list[ToolCallResult] | None = None,
    ) -> None:
        """Log a conversation turn to the log file."""
        if not self.log_path:
            return

        with self.log_path.open("a", encoding="utf-8") as f:
            if task:
                f.write(f"Turn {turn_idx} - Task: {task.task}\n")
            f.write(f"Turn {turn_idx} - User: {user_msg}\n")
            if assistant_msg:
                f.write(f"Turn {turn_idx} - Assistant: {assistant_msg}\n")
            if tool_calls:
                for tool_call in tool_calls:
                    f.write(f"Turn {turn_idx} - Tool: {tool_call.name}({tool_call.arguments})\n")

    def log_task_check(self, turn_idx: int, task_done: bool, reason: str) -> None:
        """Log task completion check result."""
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(f"Turn {turn_idx} - Task check: done={task_done} reason={reason}\n")

    def log_task_transition(self, next_task: Task) -> None:
        """Log transition to next task."""
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(f"Moving to next task: {next_task.task}\n")

    def log_tool_check(
        self,
        turn_idx: int,
        tools_used_correctly: bool,
        reason: str,
        tool_calls: list[ToolCallResult],
    ) -> None:
        """Log tool usage check result."""
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                tool_names = [tc.name for tc in tool_calls] if tool_calls else []
                f.write(
                    f"Turn {turn_idx} - Tool check: appropriate={tools_used_correctly} "
                    f"tools_called={tool_names} reason={reason}\n"
                )

    def finalize_session(self) -> None:
        """Finalize the logging session."""
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                end_time = datetime.now(ZoneInfo("Europe/Warsaw")).isoformat()
                f.write(f"Session end: {end_time}\n")
