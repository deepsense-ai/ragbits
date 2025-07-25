"""
Ragbits Core Example: Text Prompt

This example demonstrates how to use the `Prompt` class to generate themed text using an LLM.
We define an `AnimalPrompt` that generates names for a given animal type.

To run the script, execute the following command:

    ```bash
    uv run examples/core/prompt/text.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
# ]
# ///

import asyncio

from pydantic import BaseModel

from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class AnimalPromptInput(BaseModel):
    """
    Input format for the AnimalPrompt.
    """

    animal: str


class AnimalPromptOutput(BaseModel):
    """
    Output format for the AnimalPrompt.
    """

    name: str


class AnimalPrompt(Prompt[AnimalPromptInput, AnimalPromptOutput]):
    """
    Prompt that generates animal names.
    """

    system_prompt = """
    You are an animal name generator. Use provided animal kind as a base.
    """

    user_prompt = """
    Animal: {{ animal }}
    """


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    prompt = AnimalPrompt(AnimalPromptInput(animal="cat"))
    response = await llm.generate(prompt)
    print(response.name)


if __name__ == "__main__":
    asyncio.run(main())
