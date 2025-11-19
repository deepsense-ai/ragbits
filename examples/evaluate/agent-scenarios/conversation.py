"""Conversation logic for agent scenarios."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

if TYPE_CHECKING:
    pass

# Import models and logger (works with both normal imports and importlib)
try:
    from .logger import ConversationLogger
    from .models import Scenario, Task, Turn
except ImportError:
    # Fallback for importlib loading
    from logger import ConversationLogger  # noqa: E402
    from models import Scenario, Task, Turn  # noqa: E402


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


def build_llm(model_name: str | None, default_model: str, api_key: str) -> LiteLLM:
    """Build an LLM instance with the specified model name or default."""
    model = model_name or default_model
    return LiteLLM(model_name=model, use_structured_output=True, api_key=api_key)


async def run_duet(
    scenario: Scenario,
    agent: Agent,
    prompt_input_class: type[Any],  # noqa: ANN401
    max_turns: int = 10,
    log_file: str | None = None,
    agent_model_name: str | None = None,
    sim_user_model_name: str | None = None,
    checker_model_name: str | None = None,
    default_model: str = "gpt-4o-mini",
    api_key: str = "",
    user_message_prefix: str = "",
) -> None:
    """Run a conversation between an agent and a simulated user.

    The conversation proceeds through tasks defined in the scenario, with a goal checker
    determining when each task is completed. The conversation is logged if a log file is provided.

    Args:
        scenario: The scenario containing tasks to complete
        agent: The agent to interact with
        prompt_input_class: The class to use for creating prompt inputs
        max_turns: Maximum number of conversation turns
        log_file: Optional path to log file
        agent_model_name: Optional override for agent LLM model name
        sim_user_model_name: Optional override for simulated user LLM model name
        checker_model_name: Optional override for goal checker LLM model name
        default_model: Default LLM model name
        api_key: API key for LLM
        user_message_prefix: Optional prefix to add to user messages before sending to agent
    """
    # Simulated user uses an independent llm (can share the same provider)
    sim_user = SimulatedUser(llm=build_llm(sim_user_model_name, default_model, api_key), scenario=scenario)
    # Independent goal checker model
    goal_checker = GoalChecker(llm=build_llm(checker_model_name, default_model, api_key), scenario=scenario)

    history: list[Turn] = []
    logger = ConversationLogger(log_file)
    logger.initialize_session(scenario, agent_model_name, sim_user_model_name, checker_model_name)

    # Seed: ask the simulated user for the first message based on the first task
    user_message = await sim_user.next_message(history=[])

    for turn_idx in range(1, max_turns + 1):
        current_task = sim_user.get_current_task()
        if current_task is None:
            print("\nAll tasks completed!")
            break

        print(f"\n=== Turn {turn_idx} ===")
        print(f"Current Task: {current_task.task}")
        print(f"User: {user_message}")

        # Add optional prefix to user message
        full_user_message = user_message_prefix + user_message if user_message_prefix else user_message
        prompt_input = prompt_input_class(input=full_user_message)
        assistant_reply_parts: list[str] = []

        async for chunk in agent.run_streaming(prompt_input):
            if isinstance(chunk, str):
                assistant_reply_parts.append(chunk)

        assistant_reply = "".join(assistant_reply_parts).strip()
        print(f"Assistant: {assistant_reply}")
        logger.log_turn(turn_idx, current_task, user_message, assistant_reply)

        history.append(Turn(user=user_message, assistant=assistant_reply))

        # Ask the judge if current task is achieved
        task_done, reason = await goal_checker.is_task_achieved(current_task, history)
        logger.log_task_check(turn_idx, task_done, reason)
        if task_done:
            print(f"Task completed: {reason}")
            has_next = sim_user.advance_to_next_task()
            if not has_next:
                print("\nAll tasks completed!")
                break
            next_task = sim_user.get_current_task()
            if next_task:
                logger.log_task_transition(next_task)

        # Ask the simulator for the next user message
        user_message = await sim_user.next_message(history)

    else:
        print("\nReached maximum number of turns. Exiting.")

    logger.finalize_session()

