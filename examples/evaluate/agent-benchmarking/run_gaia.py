"""
Ragbits Evaluation Example: GAIA (Agent vs TodoAgent)

This example demonstrates how to evaluate the GAIA benchmark using either a classic
`Agent` or a task-decomposing `TodoAgent`, controlled by a command-line flag. Both modes
share the same prompt, retrieval setup, and parsing logic.

To run the script, execute one of the following commands:

    ```bash
    # Agent mode
    uv run python examples/evaluate/agent-benchmarking/run_gaia.py

    # TodoAgent mode
    uv run python examples/evaluate/agent-benchmarking/run_gaia.py --use_todo
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
import json
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from todo_agent import TodoAgent

from ragbits.agents import Agent, AgentOptions
from ragbits.agents.tools.openai import get_web_search_tool
from ragbits.core.llms import LiteLLM
from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.evaluate.dataloaders.gaia import GaiaDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.gaia import GaiaEfficiency, GaiaOutcome, GaiaTooling
from ragbits.evaluate.pipelines.gaia import GaiaPipeline

# Extra Agent tools


def add(a: int, b: int) -> int:
    """Add two integers and return the result."""
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract two integers and return the result (a - b)."""
    return a - b


def multiply(a: int, b: int) -> int:
    """Multiply two integers and return the result."""
    return a * b


def divide(a: int, b: int) -> float:
    """Divide two integers and return the result as float."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


def modulus(a: int, b: int) -> int:
    """Compute remainder of a divided by b (a % b)."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a % b


def _http_get(url: str, timeout: float = 10.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ragbits-agents/extra-tools"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def arxiv_search(query: str, max_results: int = 3) -> dict[str, Any]:
    """Search arXiv and return up to `max_results` entries (title, summary, link)."""
    if max_results <= 0:
        return {"results": []}

    base = "https://export.arxiv.org/api/query"
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    raw = _http_get(f"{base}?{params}")

    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        link_el = entry.find("atom:link[@rel='alternate']", ns)
        link = link_el.get("href") if link_el is not None else ""
        results.append({"title": title, "summary": summary, "link": link})

    return {"results": results}


def wiki_search(query: str, max_results: int = 2, language: str = "en") -> dict[str, Any]:
    """Search Wikipedia and return up to `max_results` entries (title and url)."""
    if max_results <= 0:
        return {"results": []}

    api = f"https://{language}.wikipedia.org/w/api.php"
    params = urllib.parse.urlencode(
        {
            "action": "opensearch",
            "search": query,
            "limit": max_results,
            "namespace": 0,
            "format": "json",
        }
    )
    raw = _http_get(f"{api}?{params}")
    data = json.loads(raw.decode("utf-8"))

    titles: list[str] = data[1] if len(data) > 1 else []
    urls: list[str] = data[3] if len(data) > 3 else []

    results: list[dict[str, Any]] = []
    for i, title in enumerate(titles[:max_results]):
        url = urls[i] if i < len(urls) else ""
        results.append({"title": title, "url": url})

    return {"results": results}


def get_extra_instruction_tpl() -> str:
    """Generate tool usage instructions template for arithmetic and lookups."""
    return (
        "Tools (use when needed):\n"
        "- add(a, b), subtract(a, b), multiply(a, b), divide(a, b), modulus(a, b)\n"
        "- arxiv_search(query, max_results=3)\n"
        "- wiki_search(query, max_results=2, language='en')\n"
        "- web_search -> OpenAI websearch tool\n"
    )


def _build_system_prompt() -> str:
    """Build a unified GAIA system prompt shared by both modes."""
    gaia_prompt = (
        "You are a general AI assistant. Provide a concise solution and finish with:\n"
        "FINAL ANSWER: [your final answer].\n"
        "Rules for FINAL ANSWER: use digits for numbers (no units unless requested);\n"
        "prefer few words for strings; for lists, return a comma-separated list."
    )

    return "\n".join(
        [
            gaia_prompt,
            get_extra_instruction_tpl(),
        ]
    )


def _build_tools() -> list:
    """Return the shared toolset for GAIA."""
    return [
        add,
        subtract,
        multiply,
        divide,
        modulus,
        arxiv_search,
        wiki_search,
        get_web_search_tool(model_name="gpt-4.1-mini"),
    ]


def _parse_final_answer(text: str) -> str:
    """Extract the FINAL ANSWER segment from model output."""
    marker = "FINAL ANSWER:"
    idx = text.rfind(marker)
    if idx == -1:
        return text.strip()
    candidate = text[idx + len(marker) :].strip()
    if candidate.startswith("[") and candidate.endswith("]"):
        candidate = candidate[1:-1].strip()
    return candidate


async def main(use_todo: bool) -> None:
    """Run GAIA evaluation in classic or Todo mode."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    base_agent: Agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=_build_system_prompt(),
        tools=_build_tools(),
        default_options=AgentOptions(max_turns=30),
    )
    evaluation_target = TodoAgent(agent=base_agent, domain_context="general AI assistant") if use_todo else base_agent

    # Data loader
    source = HuggingFaceSource(path="gaia-benchmark/GAIA", name="2023_level1", split="validation")
    dataloader = GaiaDataLoader(source=source, split="data[:10]", skip_file_attachments=True)

    # Pipeline
    log_file = "gaia_todo_examples.ndjson" if use_todo else "gaia_examples.ndjson"
    log_path = Path(__file__).with_name(log_file)
    pipeline = GaiaPipeline(
        evaluation_target=evaluation_target,
        per_example_log_file=log_path,
        extended_logs=use_todo,
        parse_answer_fn=_parse_final_answer,
    )

    # Metrics
    metrics = MetricSet(GaiaOutcome(), GaiaTooling(), GaiaEfficiency())

    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")

    if use_todo:
        await _print_todo_stats(log_path, dataloader)


async def _print_todo_stats(log_path: Path, dataloader) -> None:
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
    parser = argparse.ArgumentParser(description="GAIA evaluation example")
    parser.add_argument("--use_todo", action="store_true", help="Run with TodoAgent instead of Agent")
    args = parser.parse_args()

    asyncio.run(main(args.use_todo))
