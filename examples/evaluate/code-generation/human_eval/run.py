import asyncio
import logging
from pathlib import Path

from ragbits.agents import Agent, AgentOptions
from ragbits.agents.tools.todo import TodoList, create_todo_manager, get_todo_instruction_tpl
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

    todo_list = TodoList()
    todo_manager = create_todo_manager(todo_list)

    prompt_text = "\n".join(
        [
            """
            You are an expert Python engineer.
            Your task is to implement exactly one function that solves the problem.
            Return ONLY the function as plain Python (no markdown). Include all necessary imports.

            WORKFLOW:
            1. If query is complex you have access to todo_manager tool to create a todo list with specific tasks
            2. If query is simple question, you work without todo_manager tool, just answer the question
            3. If you use todo_manager tool, you must follow the todo workflow

            Tool policy:
            - If the problem is complex, follow this strict TODO workflow:
              1) todo_manager(action="create", tasks=[...]) with 3-5 concrete tasks
              2) For EACH task:
                 - todo_manager(action="get_current")
                 - todo_manager(action="start_task")
                 - do the work
                 - todo_manager(action="complete_task", summary="...")
              3) Finally: todo_manager(action="get_final_summary")
            - Never call complete_task before start_task.
            - If you decide to skip tools, do not call them at all.
            """,
            get_todo_instruction_tpl(task_range=(3, 5)),
        ]
    )

    agent: Agent = Agent(
        llm=LiteLLM("gpt-4.1-mini"),
        prompt=prompt_text,
        tools=[todo_manager],
        default_options=AgentOptions(max_turns=30),
    )

    # Data
    source = HuggingFaceSource(path="openai/openai_humaneval", split="test")
    dataloader = HumanEvalDataLoader(source=source, split="data[:2]")

    # Pipeline
    log_path = Path(__file__).with_name("humaneval_examples.ndjson")
    pipeline = HumanEvalPipeline(
        evaluation_target=agent,
        n_samples=1,
        timeout_sec=30,
        temperature=0.7,
        seed=42,
        per_example_log_file=log_path,
        # agent specific ext. logs
        extended_logs=False, # includes traces, tool usage, etc.
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
