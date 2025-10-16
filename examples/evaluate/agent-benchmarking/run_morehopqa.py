"""
Ragbits Evaluation Example: MoreHopQA

This example evaluates MoreHopQA using any agent provided via a path compatible with
the CLI's `import_agent_from_path` utility, e.g.:

uv run python examples/evaluate/agent-benchmarking/run_morehopqa.py \
    --agent_path examples/evaluate/agent-benchmarking/example_agents.py:morehopqa_agent

You can also specify a range of examples:

uv run python examples/evaluate/agent-benchmarking/run_morehopqa.py \
    --agent_path examples/evaluate/agent-benchmarking/example_agents.py:morehopqa_agent \
    --start_idx 0 \
    --end_idx 10

To use the Todo-enabled variant, pass `morehopqa_todo_agent`. The script will
conditionally print TODO stats when the agent is Todo-based and extended logs
are enabled.

MoreHopQA is a multi-hop reasoning benchmark that tests an agent's ability to follow
chains of reasoning over several steps.
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
from ragbits.core.sources.git import GitSource
from ragbits.evaluate.dataloaders.morehopqa import MoreHopQADataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.morehopqa import MoreHopQAEfficiency, MoreHopQAOutcome, MoreHopQATooling
from ragbits.evaluate.pipelines.morehopqa import MoreHopQAPipeline


async def main(
    agent_path: str | None,
    start_idx: int | None,
    end_idx: int | None,
) -> None:
    """Run MoreHopQA evaluation with a pluggable agent."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    default_agent_path = "examples/evaluate/agent-benchmarking/example_agents.py:morehopqa_agent"
    evaluation_target: Agent = import_agent_from_path(agent_path or default_agent_path)

    source = GitSource(
        repo_url="https://github.com/Alab-NII/morehopqa.git", file_path="datasets/files/morehopqa_final_150samples.json"
    )

    dataloader = MoreHopQADataLoader(
        source=source,
        split="data",
        start_idx=start_idx,
        end_idx=end_idx,
    )

    # Pipeline
    use_todo = evaluation_target.__class__.__name__ == "TodoAgent"
    log_file = "morehopqa_todo_examples.ndjson" if use_todo else "morehopqa_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)

    pipeline = MoreHopQAPipeline(
        evaluation_target=evaluation_target,
        per_example_log_file=log_path,
        extended_logs=use_todo,
    )

    # Metrics
    metrics = MetricSet(MoreHopQAOutcome(), MoreHopQATooling(), MoreHopQAEfficiency())

    evaluator = Evaluator(batch_size=1, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("\nMetrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")

    if use_todo:
        from utils import print_todo_stats

        await print_todo_stats(log_path, dataloader)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoreHopQA evaluation")
    parser.add_argument(
        "--agent_path",
        type=str,
        default=None,
        help=("Path to agent 'path/to/file.py:var'. " "Defaults to exported morehopqa_agent in example_agents."),
    )
    parser.add_argument(
        "--start_idx",
        type=int,
        default=None,
        help="Starting index for examples to evaluate. Defaults to 0.",
    )
    parser.add_argument(
        "--end_idx",
        type=int,
        default=None,
        help="Ending index for examples to evaluate. If not specified, all examples are used.",
    )
    args = parser.parse_args()

    asyncio.run(main(args.agent_path, args.start_idx, args.end_idx))
