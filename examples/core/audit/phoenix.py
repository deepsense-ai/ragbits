"""
Ragbits Core Example: Arize Phoenix Audit

This example demonstrates how to collect traces using Ragbits audit module with Arize Phoenix.
We run a simple LLM generation to collect telemetry data, which is then sent to the Phoenix server.

The script exports traces to the local Phoenix server running on http://localhost:6006.
You need to have Phoenix running locally:

    ```bash
    pip install arize-phoenix
    python -m phoenix.server.main serve
    ```

To run the script, execute the following command:

    ```bash
    uv run examples/core/audit/phoenix.py
    ```

To visualize the traces:
    1. Open your browser and navigate to http://localhost:6006.
    2. Check the Projects tab (default project).
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[phoenix]",
#     "tqdm",
# ]
# ///

import asyncio
from collections.abc import AsyncGenerator

from pydantic import BaseModel
from tqdm.asyncio import tqdm

from ragbits.core.audit import set_trace_handlers, traceable
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class QuestionPromptInput(BaseModel):
    """
    Input schema for the question prompt.
    """

    question: str


class QuestionPrompt(Prompt[QuestionPromptInput, str]):
    """
    A simple prompt for answering questions.
    """

    system_prompt = "You are a helpful assistant."
    user_prompt = "Question: {{ question }}"


@traceable
async def process_request() -> None:
    """
    Process an example request.
    """
    llm = LiteLLM(model_name="gpt-3.5-turbo")

    # Simple generation
    prompt = QuestionPrompt(QuestionPromptInput(question="What is the capital of France?"))
    await llm.generate(prompt)

    # You can also use explicit tracing context
    # with trace("my_custom_span") as span:
    #     ...


async def main() -> None:
    """
    Run the example.
    """
    # Ragbits observability setup
    # This automatically sets up the OpenTelemetry TracerProvider pointing to Phoenix default (localhost:6006)
    set_trace_handlers("phoenix")

    print("Running requests... Make sure Phoenix is running at http://localhost:6006")

    async def run() -> AsyncGenerator:
        for _ in range(3):
            await process_request()
            yield

    async for _ in tqdm(run()):
        pass


if __name__ == "__main__":
    asyncio.run(main())
