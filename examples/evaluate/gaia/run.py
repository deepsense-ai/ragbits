import asyncio
import logging
from pathlib import Path

from ragbits.agents import Agent, AgentOptions
from ragbits.agents.tools.extra import (
    add,
    arxiv_search,
    divide,
    get_extra_instruction_tpl,
    modulus,
    multiply,
    subtract,
    wiki_search,
)
from ragbits.agents.tools.openai import get_web_search_tool
from ragbits.agents.tools.todo import TodoList, create_todo_manager, get_todo_instruction_tpl
from ragbits.core.llms import LiteLLM
from ragbits.core.sources.hf import HuggingFaceSource
from ragbits.evaluate.dataloaders.gaia import GaiaDataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.metrics.gaia import GaiaEfficiency, GaiaOutcome, GaiaTooling
from ragbits.evaluate.pipelines.gaia import GaiaPipeline


async def main() -> None:
    """Run GAIA example with an Agent and print aggregate metrics."""
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    todo_list = TodoList()
    todo_manager = create_todo_manager(todo_list)

    gaia_prompt = (
        "You are a general AI assistant. I will ask you a question. "
        "Report your thoughts, and finish your answer with the following template: "
        "FINAL ANSWER: [YOUR FINAL ANSWER]. YOUR FINAL ANSWER should be a number OR as few words as possible "
        "OR a comma separated list of numbers and/or strings. If you are asked for a number, don't use comma to write "
        "your number neither use units such as $ or percent sign unless specified otherwise. If you are asked for a "
        "string, don't use articles, neither abbreviations (e.g. for cities), and write the digits in plain text "
        "unless specified otherwise. If you are asked for a comma separated list, apply the above rules depending of "
        "whether the element to be put in the list is a number or a string. If you are asked for a number, make sure "
        "you respond using digits not text, and ensure the answer is in appropriate unit context wise "
        "(e.g. if asked for thousands of meters and your answer is 31000, answer 31)."
    )

    system_prompt = "\n".join(
        [
            gaia_prompt,
            (
                "Tool usage:\n"
                "- Use arithmetic tools for calculations.\n"
                "- Use arxiv_search/wiki_search to retrieve relevant facts when needed or explicitly asked.\n"
                "- For multi-step/complex requests, start and manage work with the todo_manager workflow.\n"
                "- For general web-search questions, use search_web tool and gather information."
            ),
            get_todo_instruction_tpl(task_range=(3, 5)),
            get_extra_instruction_tpl(),
        ]
    )

    web_search = get_web_search_tool(model_name="gpt-4.1-mini")

    agent: Agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=system_prompt,
        tools=[
            todo_manager,
            web_search,
            add,
            subtract,
            multiply,
            divide,
            modulus,
            arxiv_search,
            wiki_search,
        ],
        default_options=AgentOptions(max_turns=30),
    )

    level = 1
    config_name = {1: "2023_level1", 2: "2023_level2", 3: "2023_level3"}[level]
    source = HuggingFaceSource(path="gaia-benchmark/GAIA", name=config_name, split="validation")
    dataloader = GaiaDataLoader(source=source, split="data[:30]", skip_file_attachments=True)

    log_path = Path(__file__).with_name("gaia_examples.ndjson")

    def parse_final_answer(text: str) -> str:
        marker = "FINAL ANSWER:"
        idx = text.rfind(marker)
        if idx == -1:
            return text.strip()
        candidate = text[idx + len(marker) :].strip()
        if candidate.startswith("[") and candidate.endswith("]"):
            candidate = candidate[1:-1].strip()
        return candidate

    pipeline = GaiaPipeline(
        evaluation_target=agent,
        per_example_log_file=log_path,
        # agent specific ext. logs
        extended_logs=False, # includes traces, tool usage, etc.
        parse_answer_fn=parse_final_answer,
    )

    metrics = MetricSet(GaiaOutcome(), GaiaTooling(), GaiaEfficiency())

    evaluator = Evaluator(batch_size=5, parallelize_batches=True)
    results = await evaluator.compute(pipeline=pipeline, dataloader=dataloader, metricset=metrics)

    print("Metrics:")
    for key, value in results.metrics.items():
        print(f"  {key}: {value:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
