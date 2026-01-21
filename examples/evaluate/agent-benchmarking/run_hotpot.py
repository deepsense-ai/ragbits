"""
Ragbits Evaluation Example: HotpotQA

This example evaluates HotpotQA using any agent provided via a path compatible
with the CLI's `import_agent_from_path` utility, e.g.:

uv run python examples/evaluate/agent-benchmarking/run_hotpot.py \
    --agent_path examples/evaluate/agent-benchmarking/example_agents.py:hotpot_agent

If you want to use the Todo-enabled variant, pass `hotpot_todo_agent` instead.
The script will conditionally print TODO stats when the agent is Todo-based and
extended logs are enabled.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-agents",
#     "ragbits-core",
#     "ragbits-document-search",
#     "ragbits-evaluate",
# ]
# ///

import argparse
import asyncio
import logging
from pathlib import Path

from utils import build_hotpot_retriever, print_todo_stats

from ragbits.agents import Agent
from ragbits.agents.cli import import_agent_from_path
from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.evaluate.dataloaders.hotpot_qa import HotpotQADataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.hotpot_qa import HotpotQAExactMatch, HotpotQAF1
from ragbits.evaluate.pipelines.hotpot_qa import HotpotQAPipeline


async def main(agent_path: str | None) -> None:
    """Run HotpotQA evaluation with a pluggable agent."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    # Load agent from path or fall back to default exported example agent
    default_agent_path = "examples/evaluate/agent-benchmarking/example_agents.py:hotpot_agent"
    evaluation_target: Agent = import_agent_from_path(agent_path or default_agent_path)

    # Data loader
    source = HuggingFaceSource(path="hotpotqa/hotpot_qa", name="distractor", split="validation")
    dataloader = HotpotQADataLoader(source=source, split="data[:5]", level_filter="hard")

    # Pipeline
    use_todo = evaluation_target.__class__.__name__ == "TodoAgent"
    log_file = "hotpot_todo_examples.ndjson" if use_todo else "hotpot_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)

    pipeline = HotpotQAPipeline(
        evaluation_target=evaluation_target,
        retriever=build_hotpot_retriever(),
        hops=3,
        per_example_log_file=log_path,
        extended_logs=use_todo,
        parse_answer_fn=evaluation_target.parse_final_answer,
        question_generation_prompt_fn=evaluation_target.question_generation_prompt_fn,
    )

    # Metrics
    metrics = MetricSet(HotpotQAExactMatch(), HotpotQAF1())

    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")

    if use_todo:
        await print_todo_stats(log_path, dataloader)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HotpotQA evaluation")
    parser.add_argument(
        "--agent_path",
        type=str,
        default=None,
        help=("Path to agent 'path/to/file.py:var'. Defaults to exported hotpot_agent in example_agents."),
    )
    args = parser.parse_args()

    asyncio.run(main(args.agent_path))
