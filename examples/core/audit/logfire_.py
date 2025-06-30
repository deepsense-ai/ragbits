"""
Ragbits Core Example: Logfire Audit

This example demonstrates how to collect traces and metrics using Ragbits audit module with Logfire.
We run the LLM generation several times to emit telemetry data, which is automatically captured by Logfire.

Before running the script, follow these steps:

    1. Open your browser and navigate to https://logfire.dev.
    2. Log in (or sign up) and create a new project.
    3. Create a new project dashboard based on the "Basic System Metrics (Logfire)" template.
    4. Create a new write token in your project settings and set it as an environment variable:

    ```bash
    export LOGFIRE_TOKEN=<your-logfire-write-token>
    ```

To run the script, execute the following command:

    ```bash
    uv run examples/core/audit/logfire_.py
    ```

To visualize the metrics collected by Ragbits, follow these steps:

    1. Navigate to your project in Logfire.
    2. To check collected traces, go to the Live section in the top bar.
    3. To check collected metrics, go to the Dashboards section and select the dashboard you created before.
"""  # noqa: E501

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core[logfire]",
#     "google-auth>=2.35.0",
#     "tqdm",
# ]
# ///

import asyncio
from collections.abc import AsyncGenerator

from pydantic import BaseModel
from tqdm.asyncio import tqdm

from ragbits.core.audit import set_metric_handlers, set_trace_handlers, traceable
from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt

# Ragbits observability setup
set_trace_handlers("logfire")
set_metric_handlers("logfire")


class DinnerIdeaPromptInput(BaseModel):
    """
    Input format for the dinner idea prompt.
    """

    chef_type: str
    ingredients: list[str]


class PromptOutput(BaseModel):
    """
    Output format for the dinner idea prompt.
    """

    answer: str


class DinnerIdeaPrompt(Prompt[DinnerIdeaPromptInput, PromptOutput]):
    """
    The dinner idea prompt.
    """

    system_prompt = """
    You are a {{ chef_type }}. Suggest a tasty dinner using only the ingredients provided.
    """
    user_prompt = """
    Available ingredients:
    {% for item in ingredients %}
        - {{ item }}
    {% endfor %}
    """


class AssistantPromptInput(BaseModel):
    """
    Input format for the assistant prompt.
    """

    suggestions: list[str]


class AssistantPrompt(Prompt[AssistantPromptInput, PromptOutput]):
    """
    The assistant prompt.
    """

    system_prompt = """
    You are an experienced home chef.
    Based on the dinner suggestions provided by different culinary experts,
    combine their ideas into one practical and delicious dinner recipe.
    """
    user_prompt = """
    Suggestions:
    {% for suggestion in suggestions %}
         - {{ suggestion }}
    {% endfor %}
    """


@traceable
async def process_request() -> None:
    """
    Process an example request.
    """
    ingredients = ["eggs", "bread", "cheddar cheese", "tomatoes"]
    chefs = [
        LiteLLM(model_name="gpt-4.1-2025-04-14", use_structured_output=True),
        LiteLLM(model_name="claude-3-7-sonnet-20250219", use_structured_output=True),
        LiteLLM(model_name="gemini-2.0-flash", use_structured_output=True),
    ]
    prompts = [
        DinnerIdeaPrompt(DinnerIdeaPromptInput(chef_type=chef_type, ingredients=ingredients))
        for chef_type in ["busy parent", "budget cook", "Michelin chef"]
    ]
    responses = await asyncio.gather(*[llm.generate(prompt) for llm, prompt in zip(chefs, prompts, strict=False)])

    assistant = LiteLLM(model_name="o3", use_structured_output=True)
    prompt = AssistantPrompt(AssistantPromptInput(suggestions=[response.answer for response in responses]))
    async for _ in assistant.generate_streaming(prompt):
        pass


async def main() -> None:
    """
    Run the example.
    """

    async def run() -> AsyncGenerator:
        for _ in range(5):
            await process_request()
            yield

    async for _ in tqdm(run()):
        pass


if __name__ == "__main__":
    asyncio.run(main())
