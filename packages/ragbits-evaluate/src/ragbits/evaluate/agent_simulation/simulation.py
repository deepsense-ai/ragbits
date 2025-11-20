"""Simulation components for agent evaluation scenarios."""

from __future__ import annotations

import json

from ragbits.agents.tool import ToolCallResult
from ragbits.core.llms import LiteLLM
from ragbits.evaluate.agent_simulation.models import Scenario, Task, Turn


class SimulatedUser:
    """A simple LLM-driven user simulator that works through tasks sequentially.

    It generates the next user utterance based on the conversation so far
    and the current task. It only moves to the next task when the current one is completed.
    """

    def __init__(self, llm: LiteLLM, scenario: Scenario) -> None:
        self.llm = llm
        self.scenario = scenario
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

        prompt = (
            "[SYSTEM]\n"
            "You are simulating a concise human user in a terminal chat. "
            f"Scenario: {self.scenario.name}\n"
            f"{task_context}\n"
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
    """

    def __init__(self, llm: LiteLLM, scenario: Scenario) -> None:
        self.llm = llm
        self.scenario = scenario

    async def is_task_achieved(self, current_task: Task, history: list[Turn]) -> tuple[bool, str]:
        """Check if the current task has been completed based on the conversation history."""
        history_text = []
        for t in history:
            history_text.append(f"User: {t.user}\nAssistant: {t.assistant}")
        history_block = "\n\n".join(history_text) if history_text else "(no prior messages)"

        prompt = (
            "[SYSTEM]\n"
            "You are a strict task-completion judge for a user-assistant conversation. "
            "Decide if the assistant has fulfilled the current task.\n"
            f"Current task: {current_task.task}\n"
            f"Expected result: {current_task.expected_result}\n\n"
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
        try:
            data = json.loads(text)
            done = bool(data.get("done", False))
            reason = str(data.get("reason", "")).strip()
        except Exception:
            # Fallback: simple heuristics
            upper = text.upper()
            if "DONE" in upper and "FALSE" not in upper:
                done = True
            reason = text
        return done, reason


class ToolUsageChecker:
    """A lightweight judge model that verifies whether the agent used the expected tools.

    It inspects the tool calls made during the conversation and checks if they match
    the expected tools for the current task.
    """

    def __init__(self, llm: LiteLLM, scenario: Scenario) -> None:
        self.llm = llm
        self.scenario = scenario

    async def check_tool_usage(
        self, current_task: Task, tool_calls: list[ToolCallResult], history: list[Turn]
    ) -> tuple[bool, str]:
        """Check if the expected tools were used for the current task."""
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

        # Use LLM to verify tool usage was appropriate for the task
        history_text = []
        for t in history:
            history_text.append(f"User: {t.user}\nAssistant: {t.assistant}")
        history_block = "\n\n".join(history_text) if history_text else "(no prior messages)"

        tool_calls_text = "\n".join([f"- {tc.name}({tc.arguments})" for tc in tool_calls])

        prompt = (
            "[SYSTEM]\n"
            "You are a tool usage evaluator for an agent conversation. "
            "Verify that the tools used by the agent were appropriate and necessary for completing the task.\n"
            f"Current task: {current_task.task}\n"
            f"Expected tools: {', '.join(expected_tool_names)}\n"
            f"Tools actually called: {', '.join(called_tool_names)}\n\n"
            "Respond with a concise JSON object ONLY, no extra text, with fields:\n"
            '{"appropriate": true|false, "reason": "short reason"}\n\n'
            "[CONVERSATION]\n"
            f"{history_block}\n\n"
            "[TOOL CALLS]\n"
            f"{tool_calls_text}\n\n"
            "[TASK]\nReturn the JSON now:"
        )

        response = await self.llm.generate(prompt=prompt)
        text = response.strip()
        # Be robust to slight deviations by attempting a minimal parse
        appropriate = True
        reason = ""
        try:
            data = json.loads(text)
            appropriate = bool(data.get("appropriate", True))
            reason = str(data.get("reason", "")).strip()
        except Exception:
            # Fallback: if all expected tools were called, consider it appropriate
            upper = text.upper()
            if "APPROPRIATE" in upper and "FALSE" in upper:
                appropriate = False
            reason = text

        if not appropriate:
            return False, f"Tool usage inappropriate: {reason}"

        return True, f"All expected tools used appropriately: {', '.join(called_tool_names)}"


def build_llm(model_name: str | None, default_model: str, api_key: str) -> LiteLLM:
    """Build an LLM instance with the specified model name or default."""
    model = model_name or default_model
    return LiteLLM(model_name=model, use_structured_output=True, api_key=api_key)
