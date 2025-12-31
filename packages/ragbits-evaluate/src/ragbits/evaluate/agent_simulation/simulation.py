"""Simulation components for agent evaluation scenarios."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms import LiteLLM
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Task, Turn

if TYPE_CHECKING:
    from ragbits.evaluate.agent_simulation.context import DataSnapshot, DomainContext


class SimulatedUser:
    """A simple LLM-driven user simulator that works through tasks sequentially.

    It generates the next user utterance based on the conversation so far
    and the current task. It only moves to the next task when the current one is completed.

    Supports optional data grounding via DataSnapshot to ensure the simulated user
    only requests items that actually exist in the available data.
    """

    def __init__(
        self,
        llm: LiteLLM,
        scenario: Scenario,
        personality: Personality | None = None,
        data_snapshot: DataSnapshot | None = None,
    ) -> None:
        """Initialize the simulated user.

        Args:
            llm: The LLM to use for generating messages.
            scenario: The scenario containing tasks to work through.
            personality: Optional personality to influence communication style.
            data_snapshot: Optional data snapshot for grounding requests to available data.
        """
        self.llm = llm
        self.scenario = scenario
        self.personality = personality
        self.data_snapshot = data_snapshot
        self.current_task_idx = 0

    def get_current_task(self) -> Task | None:
        """Get the current task, or None if all tasks are completed."""
        if self.current_task_idx < len(self.scenario.tasks):
            return self.scenario.tasks[self.current_task_idx]
        return None

    def advance_to_next_task(self) -> bool:
        """Move to the next task. Returns True if there is a next task, False otherwise."""
        if self.current_task_idx < len(self.scenario.tasks) - 1:
            self.current_task_idx += 1
            return True
        return False

    async def next_message(self, history: list[Turn]) -> str:
        """Generate the next user message based on conversation history and current task."""
        current_task = self.get_current_task()
        if current_task is None:
            return "Thank you, all tasks are completed."

        history_text = []
        for t in history:
            history_text.append(f"User: {t.user}\nAssistant: {t.assistant}")
        history_block = "\n\n".join(history_text) if history_text else "(no prior messages)"

        task_context = f"Current task: {current_task.task}"
        if self.current_task_idx > 0:
            completed_tasks = ", ".join([t.task for t in self.scenario.tasks[: self.current_task_idx]])
            task_context += f"\nCompleted tasks: {completed_tasks}"

        personality_instruction = ""
        if self.personality:
            personality_instruction = f"\n\nPersonality: {self.personality.description}"

        # Build data grounding block if snapshot is provided
        grounding_block = ""
        if self.data_snapshot:
            grounding_block = (
                "\n\n[AVAILABLE DATA]\n"
                f"{self.data_snapshot.format_for_prompt()}\n\n"
                "IMPORTANT: Only reference items that exist in the AVAILABLE DATA above. "
                "Do not ask for entities that are not listed."
            )

        prompt = (
            "[SYSTEM]\n"
            "You are simulating a concise human user in a terminal chat. "
            f"Scenario: {self.scenario.name}\n"
            f"{task_context}{personality_instruction}{grounding_block}\n"
            "Given the assistant's last reply and the conversation so far, "
            "write ONLY the next user message to work on the current task. Be specific and brief.\n\n"
            "[CONVERSATION]\n"
            f"{history_block}\n\n"
            "[TASK]\nWrite the next USER message now:"
        )

        response = await self.llm.generate(prompt=prompt)
        return response.strip()


class GoalChecker:
    """A lightweight judge model that decides whether the current task has been achieved.

    It inspects the conversation so far and checks if the task matches the expected result.
    Supports optional domain context for accurate evaluation in specific domains.
    """

    def __init__(self, llm: LiteLLM, scenario: Scenario) -> None:
        self.llm = llm
        self.scenario = scenario

    async def is_task_achieved(
        self,
        current_task: Task,
        history: list[Turn],
        context: DomainContext | None = None,
    ) -> tuple[bool, str]:
        """Check if the current task has been completed based on the conversation history.

        Args:
            current_task: The task to check completion for.
            history: List of conversation turns so far.
            context: Optional domain context for accurate evaluation (e.g., currency, locale).

        Returns:
            Tuple of (is_completed, reason).
        """
        history_text = []
        for t in history:
            history_text.append(f"User: {t.user}\nAssistant: {t.assistant}")
        history_block = "\n\n".join(history_text) if history_text else "(no prior messages)"

        # Build context block if provided
        context_block = ""
        if context:
            context_block = (
                "\n[IMPORTANT CONTEXT]\n"
                f"{context.format_for_prompt()}\n\n"
                "When evaluating task completion, consider the domain context above "
                f"and use {context.locale} locale conventions.\n\n"
            )

        prompt = (
            "[SYSTEM]\n"
            "You are a strict task-completion judge for a user-assistant conversation. "
            "Decide if the assistant has fulfilled the current task.\n"
            f"Current task: {current_task.task}\n"
            f"Expected result: {current_task.expected_result}\n"
            f"{context_block}"
            "Respond with a concise JSON object ONLY, no extra text, with fields:\n"
            '{"done": true|false, "reason": "short reason"}\n\n'
            "[CONVERSATION]\n"
            f"{history_block}\n\n"
            "[TASK]\nReturn the JSON now:"
        )

        response = await self.llm.generate(prompt=prompt)
        text = response.strip()
        # Be robust to slight deviations by attempting a minimal parse
        done = False
        reason = ""

        if not text:
            return False, "Empty response from goal checker"

        # Try to extract JSON from markdown code blocks if present
        code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if code_block_match:
            text = code_block_match.group(1)

        # Try to find JSON object in the text
        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        try:
            data = json.loads(text)
            done = bool(data.get("done", False))
            reason = str(data.get("reason", "")).strip()
        except json.JSONDecodeError:
            # If JSON parsing fails, try to infer from response text
            reason = f"Failed to parse JSON response: {text[:100]}"
            # Heuristic: if response contains "done" or "completed" or "true", assume done
            text_lower = text.lower()
            if any(word in text_lower for word in ["done", "completed", "true", "yes", "success"]):
                done = True
            elif any(word in text_lower for word in ["not done", "incomplete", "false", "no", "failed"]):
                done = False

        return done, reason


class ToolUsageChecker:
    """A simple comparator that verifies whether the agent used the expected tools.

    It checks if all expected tools from the task were called during the conversation turn.
    """

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario

    def check_tool_usage(self, current_task: Task, tool_calls: list[ToolCallResult]) -> tuple[bool, str]:  # noqa: PLR6301
        """Check if the expected tools were used for the current task.

        Args:
            current_task: The current task being evaluated
            tool_calls: List of tool calls made during this turn

        Returns:
            Tuple of (success: bool, reason: str)
        """
        if not current_task.expected_tools:
            return True, "No expected tools specified"

        if not tool_calls:
            return False, "No tools were called, but tools were expected"

        # Get the names of tools that were actually called
        called_tool_names = [tc.name for tc in tool_calls]
        expected_tool_names = current_task.expected_tools

        # Check if all expected tools were used
        missing_tools = [tool for tool in expected_tool_names if tool not in called_tool_names]

        if missing_tools:
            return (
                False,
                f"Expected tools not used: {', '.join(missing_tools)}. Tools called: {', '.join(called_tool_names)}",
            )

        return True, f"All expected tools used: {', '.join(called_tool_names)}"


def build_llm(model_name: str | None, default_model: str, api_key: str) -> LiteLLM:
    """Build an LLM instance with the specified model name or default."""
    model = model_name or default_model
    return LiteLLM(model_name=model, use_structured_output=True, api_key=api_key)
