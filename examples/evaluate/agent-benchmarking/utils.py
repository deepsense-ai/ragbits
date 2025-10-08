from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from ragbits.core.embeddings import LiteLLMEmbedder
from ragbits.core.vector_stores import VectorStoreOptions
from ragbits.core.vector_stores.in_memory import InMemoryVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.ingestion.strategies import BatchedIngestStrategy


def build_hotpot_retriever() -> DocumentSearch:
    """Create a lightweight in-memory retriever for HotpotQA."""
    return DocumentSearch(
        vector_store=InMemoryVectorStore(
            embedder=LiteLLMEmbedder(model_name="text-embedding-3-small"),
            default_options=VectorStoreOptions(k=5),
        ),
        ingest_strategy=BatchedIngestStrategy(index_batch_size=1000),
    )


class _SupportsLoad(Protocol):
    async def load(self) -> Iterable[Any]: ...


async def print_todo_stats(log_path: Path, dataloader: _SupportsLoad) -> None:
    """Print aggregated TODO-agent statistics from extended logs.

    Works across benchmarks if extended logs include the orchestrator metadata.
    """
    print("\nTODO Orchestrator Statistics:")
    decomposed_count = 0
    total_tasks = 0
    simple_count = 0
    complex_count = 0

    if log_path.exists():
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

    loaded = await dataloader.load()
    items = list(loaded)
    total = len(items)
    rate = (decomposed_count / total * 100) if total else 0.0
    avg_tasks = (total_tasks / decomposed_count) if decomposed_count else 0.0
    print(f"  Decomposition rate: {decomposed_count}/{total} ({rate:.1f}%)")
    print(f"  Average tasks per decomposed query: {avg_tasks:.1f}")
    print(f"  Complexity classification: {simple_count} simple, {complex_count} complex")
