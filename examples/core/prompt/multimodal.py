"""
Ragbits Core Example: Multimodal Prompt

This example demonstrates how to use the `Prompt` class to generate themed text using an LLM
with both text and image inputs. We define an `ImagePrompt` that generates a themed description
for a given image.

To run the script, execute the following command:

    ```bash
    uv run examples/core/prompt/multimodal.py
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
from ragbits.core.prompt import Attachment, Prompt


class ImagePromptInput(BaseModel):
    """
    Input format for the ImagePrompt.
    """

    theme: str
    image: Attachment


class ImagePromptOutput(BaseModel):
    """
    Output format for the ImagePrompt.
    """

    description: str


class ImagePrompt(Prompt[ImagePromptInput, ImagePromptOutput]):
    """
    Prompt that generates themed descriptions of images.
    """

    system_prompt = """
    You are themed image describer. Describe the image in the provided theme.
    """

    user_prompt = """
    Theme: {{ theme }}
    """


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    image = Attachment(url="https://upload.wikimedia.org/wikipedia/en/8/85/Cute_Dom_cat.JPG")
    prompt_input = ImagePromptInput(image=image, theme="dramatic")
    prompt = ImagePrompt(prompt_input)
    response = await llm.generate(prompt)
    print(response.description)


if __name__ == "__main__":
    asyncio.run(main())
