"""
Ragbits Evaluation Example: HotpotQA (Agent vs TodoAgent)

This example demonstrates how to evaluate HotpotQA using either a classic `Agent`
or a task-decomposing `TodoAgent`, selected via a command-line flag. Both modes
share the same prompt, retrieval setup, and parsing logic.

To run the script, execute one of the following commands:

    ```bash
    # Agent mode
    uv run python examples/evaluate/agent-benchmarking/run_hotpot.py

    # TodoAgent mode
    uv run python examples/evaluate/agent-benchmarking/run_hotpot.py --use_todo
    ```
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

from todo_agent import TodoAgent

from ragbits.agents import Agent, AgentOptions
from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.llms import LiteLLM
from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.core.vector_stores import VectorStoreOptions
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.ingestion.strategies import BatchedIngestStrategy
from ragbits.evaluate.dataloaders.hotpot_qa import HotpotQADataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.hotpot_qa import HotpotQAExactMatch, HotpotQAF1
from ragbits.evaluate.pipelines.hotpot_qa import HotpotQAPipeline


def _build_system_prompt() -> str:
    """Build a unified HotpotQA system prompt shared by both modes."""
    return (
        "You are a helpful assistant. Use the provided context to answer.\n"
        "Respond on a single line as: 'Answer: <final answer>'.\n"
        "- If yes/no, respond 'Answer: yes' or 'Answer: no'.\n"
        "- If a name or title is required, provide only that after 'Answer:'.\n"
        "- Do not add any extra text beyond the Answer line.\n"
        "Keep the answer concise."
    )


def _build_question_generation_prompt(original_question: str, accumulated_context: str) -> str:
    """Build a prompt for generating the next search question in multi-hop retrieval."""
    return (
        f"Original question: {original_question}\n\n"
        f"Context so far: \n{accumulated_context}\n\n"
        "Write ONE new, specific search question that fills the key missing info.\n"
        "Do not repeat known facts. Return ONLY the question."
    )


def _parse_final_answer(text: str) -> str:
    """Extract the Answer segment from model output."""
    marker = "Answer:"
    idx = text.rfind(marker)
    if idx == -1:
        return text.strip()
    candidate = text[idx + len(marker) :].strip()
    if candidate.startswith("<") and candidate.endswith(">"):
        candidate = candidate[1:-1].strip()
    return candidate


def _build_retriever() -> DocumentSearch:
    """Create a lightweight in-memory retriever for HotpotQA."""
    return DocumentSearch(
        vector_store=InMemoryVectorStore(
            embedder=LiteLLMEmbedder(model_name="text-embedding-3-small"),
            default_options=VectorStoreOptions(k=5),
        ),
        ingest_strategy=BatchedIngestStrategy(index_batch_size=1000),
    )


async def main(use_todo: bool) -> None:
    """Run HotpotQA evaluation in classic or Todo mode."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    # Build agent or TodoAgent
    base_agent: Agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=_build_system_prompt(),
        tools=[],
        default_options=AgentOptions(max_turns=5),
    )
    evaluation_target = TodoAgent(agent=base_agent, domain_context="research QA") if use_todo else base_agent

    # Data loader
    source = HuggingFaceSource(path="hotpotqa/hotpot_qa", name="distractor", split="validation")
    dataloader = HotpotQADataLoader(source=source, split="data[:10]", level_filter="hard")

    # Pipeline
    log_file = "hotpot_todo_examples.ndjson" if use_todo else "hotpot_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)
    pipeline = HotpotQAPipeline(
        evaluation_target=evaluation_target,
        retriever=_build_retriever(),
        hops=3,
        per_example_log_file=log_path,
        extended_logs=use_todo,
        parse_answer_fn=_parse_final_answer,
        question_generation_prompt_fn=_build_question_generation_prompt,
    )

    # Metrics
    metrics = MetricSet(HotpotQAExactMatch(), HotpotQAF1())

    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")

    if use_todo:
        await _print_todo_stats(log_path, dataloader)


async def _print_todo_stats(log_path: Path, dataloader: HotpotQADataLoader) -> None:
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
    parser = argparse.ArgumentParser(description="HotpotQA evaluation example")
    parser.add_argument("--use_todo", action="store_true", help="Run with TodoAgent instead of Agent")
    args = parser.parse_args()

    asyncio.run(main(args.use_todo))
