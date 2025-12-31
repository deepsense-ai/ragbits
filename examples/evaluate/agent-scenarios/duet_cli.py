"""Terminal conversation between the ragbits hotel booking agent and a simulated user."""

import argparse
import asyncio
import json

from config import config
from fixtures.hotel.hotel_chat import HotelChat

from ragbits.evaluate.agent_simulation import load_personalities, load_scenarios, run_simulation


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Two-agent terminal chat (ragbits hotel agent + simulated user)")
    parser.add_argument("--scenario-id", type=int, required=True, help="Scenario ID (1-based index)")
    parser.add_argument("--scenarios-file", type=str, default="scenarios.json", help="Path to scenarios file")
    parser.add_argument("--personality-id", type=int, help="Personality ID (1-based index, optional)")
    parser.add_argument(
        "--personalities-file", type=str, default="personalities.json", help="Path to personalities file"
    )
    parser.add_argument(
        "--max-turns-scenario", type=int, default=15, help="Max number of conversation turns for the entire scenario"
    )
    parser.add_argument("--max-turns-task", type=int, default=4, help="Max number of conversation turns per task")
    parser.add_argument("--log-file", type=str, default="duet_conversations.log", help="Path to log file")
    parser.add_argument("--agent-model-name", type=str, help="Override agent LLM model name")
    parser.add_argument("--sim-user-model-name", type=str, help="Override simulated user LLM model name")
    parser.add_argument("--checker-model-name", type=str, help="Override goal checker LLM model name")
    parser.add_argument("--output-json", type=str, help="Path to output JSON file for structured results")
    return parser.parse_args()


def main() -> None:
    """Main entry point for the simulation CLI application."""
    args = parse_args()

    # Load and validate scenario
    scenarios = load_scenarios(args.scenarios_file)
    if args.scenario_id < 1 or args.scenario_id > len(scenarios):
        raise ValueError(f"Scenario ID {args.scenario_id} out of range. Available: 1-{len(scenarios)}")
    scenario = scenarios[args.scenario_id - 1]

    # Load and validate personality (if provided)
    personality = None
    if args.personality_id is not None:
        personalities = load_personalities(args.personalities_file)
        if args.personality_id < 1 or args.personality_id > len(personalities):
            raise ValueError(f"Personality ID {args.personality_id} out of range. Available: 1-{len(personalities)}")
        personality = personalities[args.personality_id - 1]

    # Hotel-specific message prefix
    message_prefix = (
        "[STYLE]\nAnswer helpfully and clearly. "
        "Provide specific details when available (hotel names, room types, prices, dates). "
        "If information is unavailable, explain why briefly.\n\n"
    )

    hotel_chat = HotelChat(args.agent_model_name or config.llm_model, config.openai_api_key)
    result = asyncio.run(
        run_simulation(
            scenario=scenario,
            chat=hotel_chat,
            max_turns_scenario=args.max_turns_scenario,
            max_turns_task=args.max_turns_task,
            log_file=args.log_file,
            agent_model_name=args.agent_model_name,
            sim_user_model_name=args.sim_user_model_name,
            checker_model_name=args.checker_model_name,
            default_model=config.llm_model,
            api_key=config.openai_api_key,
            user_message_prefix=message_prefix,
            personality=personality,
        )
    )

    # Print summary
    print("\n=== Simulation Summary ===")
    print(f"Status: {result.status.value}")
    print(f"Tasks completed: {result.metrics.tasks_completed}/{result.metrics.total_tasks}")
    print(f"Success rate: {result.metrics.success_rate:.1%}")
    print(f"Total turns: {result.metrics.total_turns}")

    # Save to JSON if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {args.output_json}")


if __name__ == "__main__":
    main()
