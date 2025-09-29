import asyncio
import logging
from pathlib import Path

from ragbits.agents import Agent, AgentOptions
from ragbits.core.llms import LiteLLM
from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.evaluate.dataloaders.human_eval import HumanEvalDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.human_eval import HumanEvalPassAtK, HumanEvalQualityPerf
from ragbits.evaluate.pipelines.human_eval import HumanEvalPipeline


async def main() -> None:
    """Run HumanEval example with an Agent and print aggregate metrics."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    prompt_text = "\n".join(
        [
            """
            You are an expert Python engineer.
            Your task is to implement exactly one function that solves the problem.
            Return ONLY the function as plain Python (no markdown). Include all necessary imports.

            POLICY:
            - Think step-by-step internally if needed, but output only the final function.
            - Do not include explanations, comments, or markdown.
            """,
        ]
    )

    agent: Agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=prompt_text,
        tools=[],
        default_options=AgentOptions(max_turns=30),
    )

    # Data
    source = HuggingFaceSource(path="openai/openai_humaneval", split="test")
    dataloader = HumanEvalDataLoader(source=source, split="data[:2]")

    # Pipeline
    log_path = Path(__file__).with_name("humaneval_examples.ndjson")

    # Code sanitazation function
    def sanitize_code(text: str) -> str:
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

    pipeline = HumanEvalPipeline(
        evaluation_target=agent,
        n_samples=1,
        timeout_sec=30,
        per_example_log_file=log_path,
        # agent specific ext. logs
        extended_logs=True,  # includes traces, tool usage, etc.
        code_sanitize_fn=sanitize_code,
    )

    # Metrics
    metrics = MetricSet(HumanEvalPassAtK(k=1), HumanEvalPassAtK(k=5), HumanEvalQualityPerf())

    # Evaluate
    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
