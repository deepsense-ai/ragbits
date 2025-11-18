"""
Terminal conversation between the ragbits hotel booking agent and a simulated user.

Run:
    cd examples/agents/h2a

    uv run python -m duet_cli \
  --scenario-id 1 \
  --max-turns 10 \
  --agent-model-name gpt-4o-mini \
  --sim-user-model-name gpt-4o-mini \
  --checker-model-name gpt-4o-mini \
  --log-file duet_conversation.log
  --scenarios-file scenarios.json

Scenarios with tasks are defined in scenarios.json file. Use --scenario-id to select a scenario (1, 2, or 3).

"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import config
from prompt_hotel import HotelPrompt, HotelPromptInput
from tools import (
    cancel_reservation,
    create_reservation,
    get_hotel_details,
    get_reservation,
    list_cities,
    list_hotels,
    list_reservations,
    search_available_rooms,
)

from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM


@dataclass
class Turn:
    """A single conversation turn between user and assistant."""

    user: str
    assistant: str


@dataclass
class Task:
    """A single task with its expected result."""

    task: str
    expected_result: str


@dataclass
class Scenario:
    """A scenario containing multiple tasks to be completed sequentially."""

    name: str
    tasks: list[Task]


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


def _build_llm(override_model_name: str | None) -> LiteLLM:
    model = override_model_name or config.llm_model
    return LiteLLM(model_name=model, use_structured_output=True, api_key=config.openai_api_key)


def _initialize_logging(
    log_file: str | None,
    scenario: Scenario,
    agent_model_name: str | None,
    sim_user_model_name: str | None,
    checker_model_name: str | None,
) -> Path | None:
    """Initialize logging to a file if log_file is provided."""
    if not log_file:
        return None

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    now_warsaw = datetime.now(ZoneInfo("Europe/Warsaw"))
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"Session start: {now_warsaw.isoformat()}\n")
        f.write(f"Scenario: {scenario.name}\n")
        f.write(f"Tasks: {len(scenario.tasks)}\n")
        for i, task in enumerate(scenario.tasks, 1):
            f.write(f"  Task {i}: {task.task}\n")
            f.write(f"    Expected: {task.expected_result}\n")
        f.write(f"Hotel agent model: {_build_llm(agent_model_name).model_name}\n")
        f.write(f"Simulated user model: {_build_llm(sim_user_model_name).model_name}\n")
        f.write(f"Goal checker model: {_build_llm(checker_model_name).model_name}\n")
    return log_path


def _log_turn(
    log_path: Path | None,
    turn_idx: int,
    task: Task | None,
    user_msg: str,
    assistant_msg: str | None = None,
) -> None:
    """Log a conversation turn to the log file if logging is enabled."""
    if not log_path:
        return

    with log_path.open("a", encoding="utf-8") as f:
        if task:
            f.write(f"Turn {turn_idx} - Task: {task.task}\n")
        f.write(f"Turn {turn_idx} - User: {user_msg}\n")
        if assistant_msg:
            f.write(f"Turn {turn_idx} - Assistant: {assistant_msg}\n")


def _log_task_check(log_path: Path | None, turn_idx: int, task_done: bool, reason: str) -> None:
    """Log task completion check result."""
    if log_path:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"Turn {turn_idx} - Task check: done={task_done} reason={reason}\n")


def _handle_task_completion(
    log_path: Path | None,
    sim_user: SimulatedUser,
    reason: str,
) -> bool:
    """Handle task completion: advance to next task and log if needed. Returns True if all tasks done."""
    print(f"Task completed: {reason}")
    has_next = sim_user.advance_to_next_task()
    if not has_next:
        print("\nAll tasks completed!")
        return True

    if log_path:
        with log_path.open("a", encoding="utf-8") as f:
            next_task = sim_user.get_current_task()
            if next_task:
                f.write(f"Moving to next task: {next_task.task}\n")
    return False


async def run_duet(
    scenario: Scenario,
    max_turns: int = 10,
    log_file: str | None = None,
    agent_model_name: str | None = None,
    sim_user_model_name: str | None = None,
    checker_model_name: str | None = None,
) -> None:
    """Run a conversation between the hotel booking agent and a simulated user.

    The conversation proceeds through tasks defined in the scenario, with a goal checker
    determining when each task is completed. The conversation is logged if a log file is provided.
    """
    # Create the hotel booking agent directly (as ChatApp does internally)
    llm = _build_llm(agent_model_name)
    hotel_agent = Agent(
        llm=llm,
        prompt=HotelPrompt,
        tools=[
            list_cities,
            list_hotels,
            get_hotel_details,
            search_available_rooms,
            create_reservation,
            list_reservations,
            get_reservation,
            cancel_reservation,
        ],
    )

    # Simulated user uses an independent llm (can share the same provider)
    sim_user = SimulatedUser(llm=_build_llm(sim_user_model_name), scenario=scenario)
    # Independent goal checker model
    goal_checker = GoalChecker(llm=_build_llm(checker_model_name), scenario=scenario)

    history: list[Turn] = []

    # Prepare logging
    log_path = _initialize_logging(log_file, scenario, agent_model_name, sim_user_model_name, checker_model_name)

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

        concise_prefix = (
            "[STYLE]\nAnswer helpfully and clearly. "
            "Provide specific details when available (hotel names, room types, prices, dates). "
            "If information is unavailable, explain why briefly.\n\n"
        )
        prompt_input = HotelPromptInput(input=concise_prefix + user_message)
        assistant_reply_parts: list[str] = []

        async for chunk in hotel_agent.run_streaming(prompt_input):
            if isinstance(chunk, str):
                assistant_reply_parts.append(chunk)

        assistant_reply = "".join(assistant_reply_parts).strip()
        print(f"Assistant: {assistant_reply}")
        _log_turn(log_path, turn_idx, current_task, user_message, assistant_reply)

        history.append(Turn(user=user_message, assistant=assistant_reply))

        # Ask the judge if current task is achieved
        task_done, reason = await goal_checker.is_task_achieved(current_task, history)
        _log_task_check(log_path, turn_idx, task_done, reason)
        if task_done and _handle_task_completion(log_path, sim_user, reason):
            break

        # Ask the simulator for the next user message
        user_message = await sim_user.next_message(history)

    else:
        print("\nReached maximum number of turns. Exiting.")

    if log_path:
        with log_path.open("a", encoding="utf-8") as f:
            end_time = datetime.now(ZoneInfo("Europe/Warsaw")).isoformat()
            f.write(f"Session end: {end_time}\n")


def load_scenarios(scenarios_file: str = "scenarios.json") -> list[Scenario]:
    """Load scenarios from a JSON file.

    Expected JSON format:
    [
      {
        "name": "Scenario 1",
        "tasks": [
          {
            "task": "task description",
            "expected_result": "expected result description"
          },
          ...
        ]
      },
      ...
    ]
    """
    scenarios_path = Path(__file__).parent / scenarios_file
    if not scenarios_path.exists():
        raise FileNotFoundError(f"Scenarios file not found: {scenarios_path}")

    with scenarios_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Scenarios file must contain a JSON array, got {type(data).__name__}")

    scenarios: list[Scenario] = []
    for scenario_data in data:
        if not isinstance(scenario_data, dict):
            raise ValueError(f"Each scenario must be a JSON object, got {type(scenario_data).__name__}")

        name = scenario_data.get("name", "")
        tasks_data = scenario_data.get("tasks", [])

        if not isinstance(tasks_data, list):
            raise ValueError(f"Tasks must be a JSON array, got {type(tasks_data).__name__}")

        tasks: list[Task] = []
        for task_data in tasks_data:
            if not isinstance(task_data, dict):
                raise ValueError(f"Each task must be a JSON object, got {type(task_data).__name__}")

            task_desc = task_data.get("task", "")
            expected_result = task_data.get("expected_result", "")
            tasks.append(Task(task=task_desc, expected_result=expected_result))

        scenarios.append(Scenario(name=name, tasks=tasks))

    if not scenarios:
        raise ValueError(f"No scenarios found in {scenarios_path}")

    return scenarios


def parse_args() -> tuple[Scenario, int, str | None, str | None, str | None, str | None]:
    """Parse command-line arguments and return configuration for the duet conversation."""
    parser = argparse.ArgumentParser(description="Two-agent terminal chat (ragbits hotel agent + simulated user)")
    parser.add_argument(
        "--scenario-id",
        type=int,
        required=True,
        help="Scenario ID to select from scenarios.json file (1, 2, or 3)",
    )
    parser.add_argument(
        "--scenarios-file",
        type=str,
        default="scenarios.json",
        help="Path to scenarios file (default: scenarios.json)",
    )
    parser.add_argument("--max-turns", type=int, default=10, help="Max number of conversation turns")
    parser.add_argument(
        "--log-file",
        type=str,
        default="duet_conversations.log",
        help="Path to a log file to append all conversations",
    )
    parser.add_argument(
        "--agent-model-name",
        type=str,
        default=None,
        help="Override hotel agent LLM model name (defaults to config.llm_model)",
    )
    parser.add_argument(
        "--sim-user-model-name",
        type=str,
        default=None,
        help="Override simulated user LLM model name (defaults to config.llm_model)",
    )
    parser.add_argument(
        "--checker-model-name",
        type=str,
        default=None,
        help="Override goal checker LLM model name (defaults to config.llm_model)",
    )
    args = parser.parse_args()

    # Load scenarios and select the requested one
    scenarios = load_scenarios(args.scenarios_file)
    if args.scenario_id < 1 or args.scenario_id > len(scenarios):
        parser.error(f"Scenario ID {args.scenario_id} is out of range. Available scenarios: 1-{len(scenarios)}")
    scenario = scenarios[args.scenario_id - 1]  # Convert to 0-based index

    return (
        scenario,
        args.max_turns,
        args.log_file,
        args.agent_model_name,
        args.sim_user_model_name,
        args.checker_model_name,
    )


def main() -> None:
    """Main entry point for the duet CLI application."""
    scenario, max_turns, log_file, agent_model_name, sim_user_model_name, checker_model_name = parse_args()
    asyncio.run(
        run_duet(
            scenario=scenario,
            max_turns=max_turns,
            log_file=log_file,
            agent_model_name=agent_model_name,
            sim_user_model_name=sim_user_model_name,
            checker_model_name=checker_model_name,
        )
    )


if __name__ == "__main__":
    main()
