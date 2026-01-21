"""
Ragbits Evaluation Example: HumanEval

This example evaluates HumanEval using any agent provided via a path compatible
with the CLI's `import_agent_from_path` utility, e.g.:

uv run python examples/evaluate/agent-benchmarking/run_humaneval.py \
    --agent_path=examples/evaluate/agent-benchmarking/example_agents.py:humaneval_agent

To run in Todo-enabled mode, pass `humaneval_todo_agent`. The script will
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
from ragbits.evaluate.dataloaders.human_eval import HumanEvalDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.human_eval import HumanEvalPassAtK, HumanEvalQualityPerf
from ragbits.evaluate.pipelines.human_eval import HumanEvalPipeline


async def main(agent_path: str | None) -> None:
    """Run HumanEval with a pluggable agent."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    default_agent_path = "examples/evaluate/agent-benchmarking/example_agents.py:humaneval_agent"
    evaluation_target: Agent = import_agent_from_path(agent_path or default_agent_path)

    # Data
    source = HuggingFaceSource(path="openai/openai_humaneval", split="test")
    dataloader = HumanEvalDataLoader(source=source, split="data[:2]")

    # Pipeline
    use_todo = evaluation_target.__class__.__name__ == "TodoAgent"
    log_file = "humaneval_todo_examples.ndjson" if use_todo else "humaneval_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)

    pipeline = HumanEvalPipeline(
        evaluation_target=evaluation_target,
        n_samples=5,
        timeout_sec=30,
        per_example_log_file=log_path,
        extended_logs=use_todo,
        code_sanitize_fn=evaluation_target.code_sanitize_fn,
    )

    # Metrics
    metrics = MetricSet(HumanEvalPassAtK(k=1), HumanEvalPassAtK(k=5), HumanEvalQualityPerf())

    # Evaluate
    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")

    if use_todo:
        from utils import print_todo_stats  # noqa: PLC0415

        await print_todo_stats(log_path, dataloader)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HumanEval evaluation")
    parser.add_argument(
        "--agent_path",
        type=str,
        default=None,
        help=("Path to agent 'path/to/file.py:var'. Defaults to exported humaneval_agent in example_agents."),
    )
    args = parser.parse_args()

    asyncio.run(main(args.agent_path))
