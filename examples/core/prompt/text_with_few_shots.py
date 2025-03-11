"""
Ragbits Core Example: Text Prompt with Few Shots

This example shows how to use the `Prompt` class to generate themed text using an LLM.
We define a `LoremPrompt` that generates Latin-style placeholder text based on a specified theme.

The script performs the following steps:

    1. Define input and output formats using Pydantic models.
    2. Implement the `LoremPrompt` class with a structured system prompt.
    3. Provide few-shot examples to guide the model's responses.
    4. Initialize the `LiteLLM` class to generate text.
    5. Generate and a themed Lorem Ipsum response.
    6. Print the generated text.

To run the script, execute the following command:

    ```bash
    uv run examples/core/prompt/text_with_few_shots.py
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


class LoremPromptInput(BaseModel):
    """
    Input format for the LoremPrompt.
    """

    theme: str
    nsfw_allowed: bool = False


class LoremPromptOutput(BaseModel):
    """
    Output format for the LoremPrompt.
    """

    text: str


class LoremPrompt(Prompt[LoremPromptInput, LoremPromptOutput]):
    """
    Prompt that generates Lorem Ipsum text.
    """

    system_prompt = """
    You are a helpful Lorem Ipsum generator. The kind of vocabulary that you use besides "Lorem Ipsum" depends
    on the theme provided by the user. Make sure it is latin and not too long. {% if not nsfw_allowed %}Also, make sure
    that the text is safe for work.{% else %}You can use any text, even if it is not safe for work.{% endif %}
    """

    user_prompt = """
    Theme: {{ theme }}
    """

    few_shots = [
        (
            LoremPromptInput(theme="business"),
            LoremPromptOutput(text="Lorem Ipsum biznessum dolor copy machinum yearly reportum."),
        ),
        (
            LoremPromptInput(theme="technology"),
            LoremPromptOutput(text="Lorem Ipsum technologicum AI automatum neural networkum."),
        ),
        (
            LoremPromptInput(theme="health"),
            LoremPromptOutput(text="Lorem Ipsum medicorum fitnessem dietarum vitam longum."),
        ),
    ]


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    prompt = LoremPrompt(LoremPromptInput(theme="animals"))
    response = await llm.generate(prompt)
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
