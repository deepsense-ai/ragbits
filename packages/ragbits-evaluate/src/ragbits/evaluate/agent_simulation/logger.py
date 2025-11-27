"""Logging functionality for agent simulation scenarios."""

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms import Usage
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Task


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
        personality: Personality | None = None,
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
            if personality:
                f.write(f"Personality: {personality.name}\n")
                f.write(f"Personality description: {personality.description}\n")
            else:
                f.write("Personality: none (default)\n")

    def log_turn(
        self,
        turn_idx: int,
        task: Task | None,
        user_msg: str,
        assistant_msg: str | None = None,
        tool_calls: list[ToolCallResult] | None = None,
        usage: Usage | None = None,
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
            if usage:
                f.write(
                    f"Turn {turn_idx} - Assistant token usage: {usage.total_tokens} total "
                    f"({usage.prompt_tokens} prompt + {usage.completion_tokens} completion), "
                    f"estimated cost: ${usage.estimated_cost:.6f}\n"
                )

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

    def log_total_usage(self, usage: Usage) -> None:
        """Log total assistant token usage for the entire conversation."""
        if not self.log_path:
            return

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write("\n--- Total Assistant Token Usage ---\n")
            f.write(
                f"Total assistant tokens: {usage.total_tokens} "
                f"({usage.prompt_tokens} prompt + {usage.completion_tokens} completion)\n"
            )
            f.write(f"Total estimated cost: ${usage.estimated_cost:.6f}\n")
            f.write("--- End Total Assistant Token Usage ---\n")

    def log_deepeval_metrics(self, metrics: dict[str, Any] | dict[str, dict[str, float | str | None]]) -> None:
        """Log DeepEval evaluation metrics to the log file.

        Args:
            metrics: Dictionary of metric names to their evaluation results, or error dict
        """
        if not self.log_path:
            return

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write("\n--- DeepEval Evaluation Metrics ---\n")
            if "error" in metrics and isinstance(metrics["error"], str):
                # Handle error case
                f.write(f"DeepEval Error: {metrics['error']}\n")
            else:
                # Handle normal metrics case
                for metric_name, result in metrics.items():
                    if not isinstance(result, dict):
                        continue
                    score = result.get("score")
                    reason = result.get("reason")
                    success = result.get("success")
                    error = result.get("error")

                    f.write(f"Metric: {metric_name}\n")
                    if error:
                        f.write(f"  Error: {error}\n")
                    else:
                        if score is not None:
                            f.write(f"  Score: {score:.4f}\n")
                        if success is not None:
                            f.write(f"  Success: {success}\n")
                        if reason:
                            f.write(f"  Reason: {reason}\n")
            f.write("--- End DeepEval Metrics ---\n")

    def finalize_session(self) -> None:
        """Finalize the logging session."""
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                end_time = datetime.now(ZoneInfo("Europe/Warsaw")).isoformat()
                f.write(f"Session end: {end_time}\n")
