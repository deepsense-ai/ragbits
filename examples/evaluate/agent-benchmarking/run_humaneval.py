"""
Ragbits Evaluation Example: HumanEval (Agent vs TodoAgent)

This example demonstrates how to evaluate HumanEval using either a classic `Agent`
or a task-decomposing `TodoAgent`. Both modes share the
same prompt, retrieval setup, and parsing logic.

To run the script, execute one of the following commands:

    ```bash
    # Agent mode
    uv run python examples/evaluate/agent-benchmarking/run_humaneval.py

    # TodoAgent mode
    uv run python examples/evaluate/agent-benchmarking/run_humaneval.py --use_todo
    ```
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

from todo_agent import TodoAgent

from ragbits.agents import Agent, AgentOptions
from ragbits.core.llms import LiteLLM
from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.evaluate.dataloaders.human_eval import HumanEvalDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.human_eval import HumanEvalPassAtK, HumanEvalQualityPerf
from ragbits.evaluate.pipelines.human_eval import HumanEvalPipeline


def _build_system_prompt() -> str:
    """Build a unified HumanEval system prompt shared by both modes."""
    return "\n".join(
        [
            "You are an expert Python engineer.",
            "Implement exactly one function that solves the problem.",
            "Output ONLY the function as plain Python (no markdown). Include necessary imports.",
            "Do not include explanations or comments.",
        ]
    )


def _sanitize_code(text: str) -> str:
    """Remove markdown fences and keep only Python function text returned by the model."""
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if "```" in cleaned:
        start = cleaned.find("```")
        end = cleaned.find("```", start + 3)
        if end != -1:
            inside = cleaned[start + 3 : end].lstrip()
            if "\n" in inside:
                first, rest = inside.split("\n", 1)
                cleaned = rest if first.strip().lower().startswith("python") else inside
            else:
                cleaned = inside
    return cleaned.strip()


async def main(use_todo: bool) -> None:
    """Run HumanEval in classic or Todo mode."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    base_agent: Agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=_build_system_prompt(),
        tools=[],
        default_options=AgentOptions(max_turns=30),
    )
    evaluation_target = TodoAgent(agent=base_agent, domain_context="python engineer") if use_todo else base_agent

    # Data
    source = HuggingFaceSource(path="openai/openai_humaneval", split="test")
    dataloader = HumanEvalDataLoader(source=source, split="data[:2]")

    # Pipeline
    log_file = "humaneval_todo_examples.ndjson" if use_todo else "humaneval_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)
    pipeline = HumanEvalPipeline(
        evaluation_target=evaluation_target,
        n_samples=1,
        timeout_sec=30,
        per_example_log_file=log_path,
        extended_logs=use_todo,
        code_sanitize_fn=_sanitize_code,
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
        await _print_todo_stats(log_path, dataloader)


async def _print_todo_stats(log_path: Path, dataloader: HumanEvalDataLoader) -> None:
    """Print aggregated TODO-agent statistics from extended logs."""
    print("\nTODO Orchestrator Statistics:")
    decomposed_count = 0
    total_tasks = 0
    simple_count = 0
    complex_count = 0

    if log_path.exists():
        import json

        with open(log_path, encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                debug_log = record.get("extended_debug_logging", "[]")
                if debug_log and debug_log != "[]":
                    debug_data = json.loads(debug_log)
                    if debug_data and len(debug_data) > 0:
                        metadata = (debug_data[0] or {}).get("metadata", {})
                        todo_meta = metadata.get("todo", {})

                        if todo_meta.get("was_decomposed"):
                            decomposed_count += 1
                            total_tasks += int(todo_meta.get("num_tasks", 0))

                        if todo_meta.get("complexity_classification") == "SIMPLE":
                            simple_count += 1
                        elif todo_meta.get("complexity_classification") == "COMPLEX":
                            complex_count += 1

    total = len(await dataloader.load())
    rate = (decomposed_count / total * 100) if total else 0.0
    avg_tasks = (total_tasks / decomposed_count) if decomposed_count else 0.0
    print(f"  Decomposition rate: {decomposed_count}/{total} ({rate:.1f}%)")
    print(f"  Average tasks per decomposed query: {avg_tasks:.1f}")
    print(f"  Complexity classification: {simple_count} simple, {complex_count} complex")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HumanEval evaluation example")
    parser.add_argument("--use_todo", action="store_true", help="Run with TodoAgent instead of Agent")
    args = parser.parse_args()

    asyncio.run(main(args.use_todo))
