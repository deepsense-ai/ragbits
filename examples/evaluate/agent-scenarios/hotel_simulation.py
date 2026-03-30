"""Terminal conversation between the ragbits hotel booking agent and a simulated user.

Showcases all agent simulation features:
- Multiple checker types (LLM, tool_call with argument matching)
- Persona-driven simulated users
- Domain context and data snapshots for grounded evaluation
- Custom metric collectors (latency, tokens, tool usage)
- Progress callbacks for real-time monitoring
- JSON output for structured result analysis
"""

import argparse
import asyncio
import json
from typing import Any

from config import config
from fixtures.hotel.hotel_chat import HotelChat

from ragbits.evaluate.agent_simulation import (
    DataSnapshot,
    DomainContext,
    LatencyMetricCollector,
    TokenUsageMetricCollector,
    ToolUsageMetricCollector,
    load_personalities,
    load_scenarios,
    run_simulation,
)
from ragbits.evaluate.agent_simulation.models import SimulationConfig


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Hotel booking agent simulation with full feature showcase")
    parser.add_argument("--scenario-id", type=int, default=1, help="Scenario ID (1-based index, default: 1)")
    parser.add_argument("--scenarios-file", type=str, default="scenarios.json", help="Path to scenarios file")
    parser.add_argument("--persona-id", type=int, help="Persona ID (1-based index, optional)")
    parser.add_argument("--personas-file", type=str, default="personas.json", help="Path to personas file")
    parser.add_argument(
        "--max-turns-scenario", type=int, default=15, help="Max number of conversation turns for the entire scenario"
    )
    parser.add_argument("--max-turns-task", type=int, default=6, help="Max number of conversation turns per task")
    parser.add_argument("--log-file", type=str, default="duet_conversations.log", help="Path to log file")
    parser.add_argument("--agent-model-name", type=str, help="Override agent LLM model name")
    parser.add_argument("--sim-user-model-name", type=str, help="Override simulated user LLM model name")
    parser.add_argument("--checker-model-name", type=str, help="Override goal checker LLM model name")
    parser.add_argument("--output-json", type=str, help="Path to output JSON file for structured results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose progress output during simulation")
    return parser.parse_args()


async def progress_callback(**kwargs: Any) -> None:
    """Real-time progress callback for monitoring simulation events."""
    event_type = kwargs.get("event_type", "")

    if event_type == "task_complete":
        task_desc = kwargs.get("task_description", "")
        turns = kwargs.get("turns_taken", 0)
        print(f"  >> Task completed in {turns} turns: {task_desc}")

    elif event_type == "response_chunk":
        chunk_type = kwargs.get("chunk_type", "")
        if chunk_type == "checker_decision":
            print(f"  >> Checker: {kwargs.get('chunk_data', '')}")


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

    # Domain context helps the LLM checker understand hotel-specific concepts
    domain_context = DomainContext(
        domain_type="hotel_booking",
        locale="pl_PL",
        metadata={
            "currency": "PLN",
            "cities": ["Kraków", "Warszawa", "Gdańsk"],
            "room_types": ["standard", "deluxe", "suite"],
            "available_tools": [
                "list_cities",
                "list_hotels",
                "get_hotel_details",
                "search_available_rooms",
                "create_reservation",
                "list_reservations",
                "get_reservation",
                "cancel_reservation",
            ],
        },
    )

    # Data snapshot grounds the simulated user with real hotel data
    data_snapshot = DataSnapshot(
        description="Polish hotel booking system with hotels in Kraków, Warszawa, and Gdańsk",
        entities={
            "cities": ["Kraków", "Warszawa", "Gdańsk"],
            "sample_hotels": [
                "Grand Hotel Kraków (4.8 stars)",
                "Hotel Copernicus Kraków (4.9 stars)",
                "Sheraton Grand Warszawa (4.7 stars)",
                "Hotel Bristol Warszawa (4.9 stars)",
                "Hilton Gdańsk (4.7 stars)",
            ],
            "room_types": [
                "standard (250-380 PLN/night)",
                "deluxe (400-600 PLN/night)",
                "suite (600-900 PLN/night)",
            ],
            "date_range": "January 2025 - August 2025",
        },
    )

    # Build simulation config with all features enabled
    simulation_config = SimulationConfig(
        max_turns_scenario=args.max_turns_scenario,
        max_turns_task=args.max_turns_task,
        log_file=args.log_file,
        agent_model_name=args.agent_model_name,
        sim_user_model_name=args.sim_user_model_name,
        checker_model_name=args.checker_model_name,
        default_model=config.llm_model,
        api_key=config.openai_api_key,
        user_message_prefix=message_prefix,
        domain_context=domain_context,
        data_snapshot=data_snapshot,
        metrics=[LatencyMetricCollector, TokenUsageMetricCollector, ToolUsageMetricCollector],
    )

    hotel_chat = HotelChat(args.agent_model_name or config.llm_model, config.openai_api_key)
    result = asyncio.run(
        run_simulation(
            scenario=scenario,
            chat=hotel_chat,
            config=simulation_config,
            personality=persona,
            progress_callback=progress_callback if args.verbose else None,
        )
    )

    # Print summary
    print("\n=== Simulation Summary ===")
    print(f"Status: {result.status.value}")
    if result.metrics:
        print(f"Tasks completed: {result.metrics.tasks_completed}/{result.metrics.total_tasks}")
        print(f"Success rate: {result.metrics.success_rate:.1%}")
        print(f"Total turns: {result.metrics.total_turns}")

        # Print custom metrics
        metrics = result.metrics.metrics
        if metrics:
            print("\n=== Performance Metrics ===")

            # Latency metrics
            if "latency_avg_ms" in metrics:
                print(f"Latency (avg): {metrics['latency_avg_ms']:.1f}ms")
                print(f"Latency (min/max): {metrics['latency_min_ms']:.1f}ms / {metrics['latency_max_ms']:.1f}ms")

            # Token usage metrics
            if "tokens_total" in metrics:
                print(f"Tokens (total): {metrics['tokens_total']}")
                print(f"Tokens (avg/turn): {metrics['tokens_avg_per_turn']:.1f}")

            # Tool usage metrics
            if "tools_total_calls" in metrics:
                print(f"Tool calls (total): {metrics['tools_total_calls']}")
                print(f"Unique tools used: {', '.join(metrics['tools_unique'])}")
                print(f"Turns with tools: {metrics['turns_with_tools']}")

    # Save to JSON if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {args.output_json}")


if __name__ == "__main__":
    main()
