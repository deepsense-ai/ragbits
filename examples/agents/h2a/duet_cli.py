"""
Terminal conversation between the ragbits financial agent and a simulated user.

Run:
    cd examples/agents/h2a
    
    uv run python -m duet_cli \
  --goal "Get two promissing stocks for me to invest in" \
  --model-name gpt-4o-mini \
  --log-file duet_conversation.log
    

"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

from config import config
from prompt_finance import FinancePrompt, FinancePromptInput
from tools import get_yahoo_finance_markdown


@dataclass
class Turn:
    user: str
    assistant: str


class SimulatedUser:
    """A simple LLM-driven user simulator with a clear goal.

    It generates the next user utterance based on the conversation so far
    and a fixed goal string describing the intention.
    """

    def __init__(self, llm: LiteLLM, goal: str) -> None:
        self.llm = llm
        self.goal = goal

    async def next_message(self, history: List[Turn]) -> str:
        history_text = []
        for t in history:
            history_text.append(f"User: {t.user}\nAssistant: {t.assistant}")
        history_block = "\n\n".join(history_text) if history_text else "(no prior messages)"

        prompt = (
            "[SYSTEM]\n"
            "You are simulating a concise human user in a terminal chat. "
            f"Your goal is: {self.goal}. "
            "Given the assistant's last reply and the conversation so far, "
            "write ONLY the next user message. Be specific and brief. "
            "If the goal has been achieved, reply with: DONE\n\n"
            "[CONVERSATION]\n"
            f"{history_block}\n\n"
            "[TASK]\nWrite the next USER message now:"
        )

        response = await self.llm.generate(prompt=prompt)
        return response.strip()


def _build_llm(override_model_name: str | None) -> LiteLLM:
    model = override_model_name or config.llm_model
    return LiteLLM(model_name=model, use_structured_output=True, api_key=config.openai_api_key)


async def run_duet(
    goal: str,
    max_turns: int = 5,
    log_file: str | None = None,
    model_name: str | None = None,
) -> None:
    # Create the financial agent directly (as ChatApp does internally)
    llm = _build_llm(model_name)
    financial_agent = Agent(llm=llm, prompt=FinancePrompt, tools=[get_yahoo_finance_markdown])

    # Simulated user uses an independent llm (can share the same provider)
    sim_user = SimulatedUser(llm=_build_llm(model_name), goal=goal)

    history: List[Turn] = []

    # Prepare logging
    log_path: Path | None = None
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        now_warsaw = datetime.now(ZoneInfo("Europe/Warsaw"))
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Session start: {now_warsaw.isoformat()}\n")
            f.write(f"Goal: {goal}\n")
            f.write(f"Model: {llm.model_name}\n")

    # Seed: ask the simulated user for the first message based on the goal
    user_message = await sim_user.next_message(history=[])

    for turn_idx in range(1, max_turns + 1):
        print(f"\n=== Turn {turn_idx} ===")
        print(f"User: {user_message}")
        if log_path:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"Turn {turn_idx} - User: {user_message}\n")

        if user_message.upper() == "DONE":
            print("Conversation ended (user indicates goal achieved).")
            break

        concise_prefix = (
            "[STYLE]\nAnswer very concisely (<= 2 sentences). "
            "If specifics are unknown, say so briefly.\n\n"
        )
        prompt_input = FinancePromptInput(input=concise_prefix + user_message)
        assistant_reply_parts: List[str] = []

        async for chunk in financial_agent.run_streaming(prompt_input):
            if isinstance(chunk, str):
                assistant_reply_parts.append(chunk)

        assistant_reply = "".join(assistant_reply_parts).strip()
        print(f"Assistant: {assistant_reply}")
        if log_path:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"Turn {turn_idx} - Assistant: {assistant_reply}\n")

        history.append(Turn(user=user_message, assistant=assistant_reply))

        # Ask the simulator for the next user message
        user_message = await sim_user.next_message(history)

    else:
        print("\nReached maximum number of turns. Exiting.")

    if log_path:
        with log_path.open("a", encoding="utf-8") as f:
            end_time = datetime.now(ZoneInfo("Europe/Warsaw")).isoformat()
            f.write(f"Session end: {end_time}\n")


def parse_args() -> Tuple[str, int, str | None, str | None]:
    parser = argparse.ArgumentParser(description="Two-agent terminal chat (ragbits + simulated user)")
    parser.add_argument("--goal", required=True, help="Simulated user goal/intention")
    parser.add_argument("--max-turns", type=int, default=5, help="Max number of conversation turns")
    parser.add_argument(
        "--log-file",
        type=str,
        default="duet_conversations.log",
        help="Path to a log file to append all conversations",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="Override LLM model name (defaults to config.llm_model)",
    )
    args = parser.parse_args()
    return args.goal, args.max_turns, args.log_file, args.model_name


def main() -> None:
    goal, max_turns, log_file, model_name = parse_args()
    asyncio.run(run_duet(goal=goal, max_turns=max_turns, log_file=log_file, model_name=model_name))


if __name__ == "__main__":
    main()


