import asyncio
import logging
from pathlib import Path

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


async def main() -> None:
    """Run HotpotQA example with an Agent and print aggregate metrics."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    hotpot_prompt = (
        "You are a helpful assistant. Use the given context to answer.\n"
        "Respond on a single line as: 'Answer: <final answer>'.\n"
        "- If yes/no, respond 'Answer: yes' or 'Answer: no'.\n"
        "- If a name/title is required, respond only the name/title after 'Answer:'.\n"
        "- Do not add any extra text beyond the Answer line.\n"
        "- Your answer should as concise and minimal as possible, while still answering the question.\n"
        "- Think step-by-step internally for complex questions before answering concisely."
    )

    system_prompt = "\n".join(
        [
            hotpot_prompt,
        ]
    )
    agent: Agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=system_prompt,
        tools=[],
        default_options=AgentOptions(max_turns=5),
    )

    source = HuggingFaceSource(path="hotpotqa/hotpot_qa", name="distractor", split="validation")
    dataloader = HotpotQADataLoader(source=source, split="data[:25]", level_filter="hard")

    log_path = Path(__file__).with_name("hotpot_examples.ndjson")

    def parse_final_answer(text: str) -> str:
        marker = "Answer:"
        idx = text.rfind(marker)
        if idx == -1:
            return text.strip()
        candidate = text[idx + len(marker) :].strip()
        if candidate.startswith("<") and candidate.endswith(">"):
            candidate = candidate[1:-1].strip()
        return candidate

    retriever = DocumentSearch(
        vector_store=InMemoryVectorStore(
            embedder=LiteLLMEmbedder(model_name="text-embedding-3-small"),
            default_options=VectorStoreOptions(k=5),
        ),
        ingest_strategy=BatchedIngestStrategy(index_batch_size=1000),
    )

    pipeline = HotpotQAPipeline(
        evaluation_target=agent,
        retriever=retriever,
        hops=3,
        per_example_log_file=log_path,
        # agent specific ext. logs
        extended_logs=False,  # includes traces, tool usage, etc.
        parse_answer_fn=parse_final_answer,
    )

    metrics = MetricSet(HotpotQAExactMatch(), HotpotQAF1())

    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
