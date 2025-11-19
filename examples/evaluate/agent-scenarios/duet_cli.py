"""Terminal conversation between the ragbits hotel booking agent and a simulated user."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

from ragbits.agents import Agent
from ragbits.core.llms import LiteLLM

# Setup: add parent directory to path for imports
_parent_dir = Path(__file__).parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))


def _load_module(module_name: str, file_path: Path) -> Any:  # noqa: ANN401
    """Load a module using importlib and register it in sys.modules."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # Register before execution for dataclass support
    spec.loader.exec_module(module)
    return module


# Load modules (using importlib due to hyphenated directory name)
config_module = _load_module("config", _parent_dir / "config.py")
config = config_module.config  # noqa: E402

hotel_fixtures = _load_module("fixtures.hotel", _parent_dir / "fixtures" / "hotel" / "__init__.py")
HotelPrompt = hotel_fixtures.HotelPrompt  # noqa: E402
HotelPromptInput = hotel_fixtures.HotelPromptInput  # noqa: E402

# Load local modules in dependency order
_load_module("models", _parent_dir / "models.py")
_load_module("logger", _parent_dir / "logger.py")
scenarios_module = _load_module("scenarios", _parent_dir / "scenarios.py")
conversation_module = _load_module("conversation", _parent_dir / "conversation.py")

load_scenarios = scenarios_module.load_scenarios  # noqa: E402
run_duet = conversation_module.run_duet  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Two-agent terminal chat (ragbits hotel agent + simulated user)")
    parser.add_argument("--scenario-id", type=int, required=True, help="Scenario ID (1-based index)")
    parser.add_argument("--scenarios-file", type=str, default="scenarios.json", help="Path to scenarios file")
    parser.add_argument("--max-turns", type=int, default=10, help="Max number of conversation turns")
    parser.add_argument("--log-file", type=str, default="duet_conversations.log", help="Path to log file")
    parser.add_argument("--agent-model-name", type=str, help="Override agent LLM model name")
    parser.add_argument("--sim-user-model-name", type=str, help="Override simulated user LLM model name")
    parser.add_argument("--checker-model-name", type=str, help="Override goal checker LLM model name")
    return parser.parse_args()


def main() -> None:
    """Main entry point for the duet CLI application."""
    args = parse_args()

    # Load and validate scenario
    scenarios = load_scenarios(args.scenarios_file)
    if args.scenario_id < 1 or args.scenario_id > len(scenarios):
        raise ValueError(f"Scenario ID {args.scenario_id} out of range. Available: 1-{len(scenarios)}")
    scenario = scenarios[args.scenario_id - 1]

    # Create hotel booking agent
    agent = Agent(
        llm=LiteLLM(
            model_name=args.agent_model_name or config.llm_model,
            use_structured_output=True,
            api_key=config.openai_api_key,
        ),
        prompt=HotelPrompt,
        tools=[
            hotel_fixtures.list_cities,
            hotel_fixtures.list_hotels,
            hotel_fixtures.get_hotel_details,
            hotel_fixtures.search_available_rooms,
            hotel_fixtures.create_reservation,
            hotel_fixtures.list_reservations,
            hotel_fixtures.get_reservation,
            hotel_fixtures.cancel_reservation,
        ],
    )

    # Hotel-specific message prefix
    message_prefix = (
        "[STYLE]\nAnswer helpfully and clearly. "
        "Provide specific details when available (hotel names, room types, prices, dates). "
        "If information is unavailable, explain why briefly.\n\n"
    )

    asyncio.run(
        run_duet(
            scenario=scenario,
            agent=agent,
            prompt_input_class=HotelPromptInput,
            max_turns=args.max_turns,
            log_file=args.log_file,
            agent_model_name=args.agent_model_name,
            sim_user_model_name=args.sim_user_model_name,
            checker_model_name=args.checker_model_name,
            default_model=config.llm_model,
            api_key=config.openai_api_key,
            user_message_prefix=message_prefix,
        )
    )


if __name__ == "__main__":
    main()
