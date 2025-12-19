"""Simulation components for agent evaluation scenarios."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt
from ragbits.evaluate.agent_simulation.models import Personality, Scenario, Task, Turn

if TYPE_CHECKING:
    from ragbits.evaluate.agent_simulation.context import DataSnapshot


class SimulatedUserPromptInput(BaseModel):
    """Input for the simulated user prompt."""

    scenario_name: str
    task_context: str
    personality_instruction: str
    grounding_block: str
    history_block: str
    current_task: str


class SimulatedUserPrompt(Prompt[SimulatedUserPromptInput, str]):
    """Prompt for generating simulated user messages."""

    system_prompt = """
You are simulating a concise human user in a terminal chat.
Scenario: {{ scenario_name }}
{{ task_context }}{{ personality_instruction }}{{ grounding_block }}
Given the assistant's last reply and the conversation so far,
write ONLY the next user message to work on the current task. Be specific and brief.
"""

    user_prompt = """
[CONVERSATION]
{{ history_block }}

[TASK]
Write the next USER message now (follow task: {{ current_task }}):
"""


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

        prompt = SimulatedUserPrompt(
            SimulatedUserPromptInput(
                scenario_name=self.scenario.name,
                task_context=self._build_task_context(current_task),
                personality_instruction=self._build_personality_instruction(),
                grounding_block=self._build_grounding_block(),
                history_block=self._build_history_block(history),
                current_task=current_task.task,
            )
        )

        response = await self.llm.generate(prompt)
        return response.strip()

    def _build_task_context(self, current_task: Task) -> str:
        """Build the task context string."""
        task_context = f"Current task: {current_task.task}"
        if self.current_task_idx > 0:
            completed_tasks = ", ".join([t.task for t in self.scenario.tasks[: self.current_task_idx]])
            task_context += f"\nCompleted tasks: {completed_tasks}"
        return task_context

    def _build_personality_instruction(self) -> str:
        """Build the personality instruction string."""
        if self.personality:
            return f"\n\nPersonality: {self.personality.description}"
        return ""

    def _build_grounding_block(self) -> str:
        """Build the data grounding block string."""
        if not self.data_snapshot:
            return ""

        return f"""
        <AVAILABLE_DATA comment="This section lists data available for agent, not listed entities may not exist.">
            {self.data_snapshot.format_for_prompt()}
        </AVAILABLE_DATA>
        """

    @staticmethod
    def _build_history_block(history: list[Turn]) -> str:
        """Build the conversation history block string."""
        if not history:
            return "(no prior messages)"
        history_text = [f"User: {t.user}\nAssistant: {t.assistant}" for t in history]
        return "\n\n".join(history_text)


def build_llm(model_name: str | None, default_model: str, api_key: str) -> LiteLLM:
    """Build an LLM instance with the specified model name or default."""
    model = model_name or default_model
    return LiteLLM(model_name=model, use_structured_output=True, api_key=api_key)
