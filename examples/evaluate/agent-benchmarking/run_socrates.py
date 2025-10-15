"""
Ragbits Evaluation Example: SOCRATES

This example evaluates SOCRATES using any agent provided via a path compatible with
the CLI's `import_agent_from_path` utility, e.g.:

uv run python examples/evaluate/agent-benchmarking/run_socrates.py \
    --agent_path examples/evaluate/agent-benchmarking/example_agents.py:socrates_agent

To use the Todo-enabled variant, pass `socrates_todo_agent`. The script will
conditionally print TODO stats when the agent is Todo-based and extended logs
are enabled.

SOCRATES is a multi-hop reasoning benchmark that tests an agent's ability to follow
chains of reasoning over several steps. The dataset originates from Google DeepMind's
latent-multi-hop-reasoning repository available on GitHub.
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
from ragbits.evaluate.dataloaders.socrates import SocratesDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.socrates import SocratesEfficiency, SocratesOutcome, SocratesTooling
from ragbits.evaluate.pipelines.socrates import SocratesPipeline


async def main(agent_path: str | None) -> None:
    """Run SOCRATES evaluation with a pluggable agent."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    default_agent_path = "examples/evaluate/agent-benchmarking/example_agents.py:socrates_agent"
    evaluation_target: Agent = import_agent_from_path(agent_path or default_agent_path)

    source = HuggingFaceSource(path="soheeyang/SOCRATES", split="train")

    dataloader = SocratesDataLoader(
        source=source, split="data[:1]"
    )  # 9:14 includes 3 examples that didn't work for non-todo

    # Pipeline
    use_todo = evaluation_target.__class__.__name__ == "TodoAgent"
    log_file = "socrates_todo_examples.ndjson" if use_todo else "socrates_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)

    pipeline = SocratesPipeline(
        evaluation_target=evaluation_target,
        per_example_log_file=log_path,
        extended_logs=use_todo,
    )

    # Metrics
    metrics = MetricSet(SocratesOutcome(), SocratesTooling(), SocratesEfficiency())

    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")

    if use_todo:
        from utils import print_todo_stats

        await print_todo_stats(log_path, dataloader)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SOCRATES evaluation")
    parser.add_argument(
        "--agent_path",
        type=str,
        default=None,
        help=("Path to agent 'path/to/file.py:var'. " "Defaults to exported socrates_agent in example_agents."),
    )
    args = parser.parse_args()

    asyncio.run(main(args.agent_path))
