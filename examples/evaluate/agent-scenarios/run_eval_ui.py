"""Run the Evaluation UI server with the hotel booking agent."""

import argparse
import sys
from pathlib import Path

# Add parent to path so we can import config and fixtures
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from fixtures.hotel.hotel_chat import HotelChat

from ragbits.evaluate.agent_simulation.metrics.deepeval import (
    DeepEvalCompletenessMetricCollector,
    DeepEvalKnowledgeRetentionMetricCollector,
    DeepEvalRelevancyMetricCollector,
)
from ragbits.evaluate.agent_simulation.models import SimulationConfig
from ragbits.evaluate.api import EvalAPI


def create_hotel_chat() -> HotelChat:
    """Factory function to create HotelChat instances."""
    return HotelChat(model_name=config.llm_model, api_key=config.openai_api_key)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run the Evaluation UI server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8001, help="Port to bind to")
    parser.add_argument(
        "--scenarios-dir",
        type=str,
        default=str(Path(__file__).parent),
        help="Directory containing scenario JSON files",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=str(Path(__file__).parent / "eval_results"),
        help="Directory for storing evaluation results",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    print(f"Starting Eval UI server on http://{args.host}:{args.port}")
    print(f"Scenarios directory: {args.scenarios_dir}")
    print(f"Results directory: {args.results_dir}")
    print("\nOpen the frontend at: http://localhost:5173/eval.html")
    print("(Run 'npm run dev:eval' in typescript/ui/ first)\n")

    # Simulation config with DeepEval metrics available as extras
    simulation_config = SimulationConfig(
        default_model=config.llm_model,
        api_key=config.openai_api_key,
        metrics=[
            # Builtins are included by default (Latency, TokenUsage, ToolUsage)
            # DeepEval metrics available as optional extras in the UI
            DeepEvalCompletenessMetricCollector,
            DeepEvalRelevancyMetricCollector,
            DeepEvalKnowledgeRetentionMetricCollector,
        ],
    )

    api = EvalAPI(
        chat_factory=create_hotel_chat,
        scenarios_dir=args.scenarios_dir,
        results_dir=args.results_dir,
        cors_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        simulation_config=simulation_config,
    )

    api.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()

