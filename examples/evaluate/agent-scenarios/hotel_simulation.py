"""Terminal conversation between the ragbits hotel booking agent and a simulated user."""

import argparse
import asyncio
import json

from config import config
from fixtures.hotel.hotel_chat import HotelChat

from ragbits.evaluate.agent_simulation import (
    LatencyMetricCollector,
    TokenUsageMetricCollector,
    ToolUsageMetricCollector,
    load_personalities,
    load_scenarios,
    run_simulation,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Two-agent terminal chat (ragbits hotel agent + simulated user)")
    parser.add_argument("--scenario-id", type=int, required=True, help="Scenario ID (1-based index)")
    parser.add_argument("--scenarios-file", type=str, default="scenarios.json", help="Path to scenarios file")
    parser.add_argument("--persona-id", type=int, help="Persona ID (1-based index, optional)")
    parser.add_argument(
        "--personas-file", type=str, default="personas.json", help="Path to personas file"
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
    parser.add_argument(
        "--enable-metrics",
        action="store_true",
        help="Enable custom metric collectors (latency, token usage, tool usage)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the simulation CLI application."""
    args = parse_args()

    # Load and validate scenario
    scenarios = load_scenarios(args.scenarios_file)
    if args.scenario_id < 1 or args.scenario_id > len(scenarios):
        raise ValueError(f"Scenario ID {args.scenario_id} out of range. Available: 1-{len(scenarios)}")
    scenario = scenarios[args.scenario_id - 1]

    # Load and validate persona (if provided)
    persona = None
    if args.persona_id is not None:
        personas = load_personalities(args.personas_file)
        if args.persona_id < 1 or args.persona_id > len(personas):
            raise ValueError(f"Persona ID {args.persona_id} out of range. Available: 1-{len(personas)}")
        persona = personas[args.persona_id - 1]

    # Hotel-specific message prefix
    message_prefix = (
        "[STYLE]\nAnswer helpfully and clearly. "
        "Provide specific details when available (hotel names, room types, prices, dates). "
        "If information is unavailable, explain why briefly.\n\n"
    )

    # Initialize metric collectors if enabled
    metric_collectors = (
        [
            LatencyMetricCollector(),
            TokenUsageMetricCollector(),
            ToolUsageMetricCollector(),
        ]
        if args.enable_metrics
        else None
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
            personality=persona,
            metric_collectors=metric_collectors,
        )
    )

    # Print summary
    print("\n=== Simulation Summary ===")
    print(f"Status: {result.status.value}")
    print(f"Tasks completed: {result.metrics.tasks_completed}/{result.metrics.total_tasks}")
    print(f"Success rate: {result.metrics.success_rate:.1%}")
    print(f"Total turns: {result.metrics.total_turns}")

    # Print custom metrics if enabled
    if result.metrics.custom:
        print("\n=== Custom Metrics ===")
        custom = result.metrics.custom

        # Latency metrics
        if "latency_avg_ms" in custom:
            print(f"Latency (avg): {custom['latency_avg_ms']:.1f}ms")
            print(f"Latency (min/max): {custom['latency_min_ms']:.1f}ms / {custom['latency_max_ms']:.1f}ms")

        # Token usage metrics
        if "tokens_total" in custom:
            print(f"Tokens (total): {custom['tokens_total']}")
            print(f"Tokens (avg/turn): {custom['tokens_avg_per_turn']:.1f}")

        # Tool usage metrics
        if "tools_total_calls" in custom:
            print(f"Tool calls (total): {custom['tools_total_calls']}")
            print(f"Unique tools used: {', '.join(custom['tools_unique'])}")
            print(f"Turns with tools: {custom['turns_with_tools']}")

    # Save to JSON if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {args.output_json}")


if __name__ == "__main__":
    main()
