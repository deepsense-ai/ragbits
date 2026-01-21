"""
Ragbits Evaluation Example: GAIA

This example evaluates GAIA using any agent provided via a path compatible with
the CLI's `import_agent_from_path` utility, e.g.:

uv run python examples/evaluate/agent-benchmarking/run_gaia.py \
    --agent_path examples/evaluate/agent-benchmarking/example_agents.py:gaia_agent

To use the Todo-enabled variant, pass `gaia_todo_agent`. The script will
conditionally print TODO stats when the agent is Todo-based and extended logs
are enabled.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-agents",
#     "ragbits-core",
#     "ragbits-evaluate",
# ]
# ///

import argparse
import asyncio
import logging
from pathlib import Path

from ragbits.agents import Agent
from ragbits.agents.cli import import_agent_from_path
from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.evaluate.dataloaders.gaia import GaiaDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.gaia import GaiaEfficiency, GaiaOutcome, GaiaTooling
from ragbits.evaluate.pipelines.gaia import GaiaPipeline


async def main(agent_path: str | None) -> None:
    """Run GAIA evaluation with a pluggable agent."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    default_agent_path = "examples/evaluate/agent-benchmarking/example_agents.py:gaia_agent"
    evaluation_target: Agent = import_agent_from_path(agent_path or default_agent_path)

    # Data loader
    source = HuggingFaceSource(path="gaia-benchmark/GAIA", name="2023_level1", split="validation")
    dataloader = GaiaDataLoader(source=source, split="data[:10]", skip_file_attachments=True)

    # Pipeline
    use_todo = evaluation_target.__class__.__name__ == "TodoAgent"
    log_file = "gaia_todo_examples.ndjson" if use_todo else "gaia_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)

    pipeline = GaiaPipeline(
        evaluation_target=evaluation_target,
        per_example_log_file=log_path,
        extended_logs=use_todo,
        parse_answer_fn=evaluation_target.parse_final_answer,
    )

    # Metrics
    metrics = MetricSet(GaiaOutcome(), GaiaTooling(), GaiaEfficiency())

    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")

    if use_todo:
        from utils import print_todo_stats  # noqa: PLC0415

        await print_todo_stats(log_path, dataloader)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GAIA evaluation")
    parser.add_argument(
        "--agent_path",
        type=str,
        default=None,
        help=("Path to agent 'path/to/file.py:var'. Defaults to exported gaia_agent in example_agents."),
    )
    args = parser.parse_args()

    asyncio.run(main(args.agent_path))
