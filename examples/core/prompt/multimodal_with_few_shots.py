"""
Ragbits Core Example: Multimodal Prompt with Few Shots

This example demonstrates how to use the `Prompt` class to generate themed text using an LLM
with both text and image inputs. We define an `ImagePrompt` that generates a themed description
for a given image, using few-shot examples to improve response accuracy.

The script performs the following steps:

    1. Define input and output formats using Pydantic models.
    2. Implement the `ImagePrompt` class with a structured system prompt.
    3. Specify `image_url` as an input field for multimodal processing.
    4. Provide multimodal few-shot examples to guide the model's responses.
    5. Initialize the `LiteLLM` class to generate text.
    6. Generate a themed description based on the image.
    7. Print the generated description.

To run the script, execute the following command:

    ```bash
    uv run examples/core/prompt/multimodal_with_few_shots.py
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


class ImagePromptInput(BaseModel):
    """
    Input format for the ImagePrompt.
    """

    theme: str
    image_url: str


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
    You are themed image describer. Descirbe the image in the provided theme.
    """

    user_prompt = """
    Theme: {{ theme }}
    """

    image_input_fields = ["image_url"]

    few_shots = [
        (
            ImagePromptInput(
                theme="pirates",
                image_url="https://upload.wikimedia.org/wikipedia/commons/5/55/Acd_a_frame.jpg",
            ),
            ImagePromptOutput(description="Arrr, that would be a dog!."),
        ),
        (
            ImagePromptInput(
                theme="fairy tale",
                image_url="https://upload.wikimedia.org/wikipedia/commons/6/62/Red_Wolf.jpg",
            ),
            ImagePromptOutput(
                description="Once upon a time, in an enchanted forest, a noble wolf roamed under the moonlit sky."
            ),
        ),
        (
            ImagePromptInput(
                theme="sci-fi",
                image_url="https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Bruce_McCandless_II_during_EVA_in_1984.jpg/2560px-Bruce_McCandless_II_during_EVA_in_1984.jpg",
            ),
            ImagePromptOutput(
                description="A lone astronaut drifts through the void, bathed in the eerie glow of distant galaxies."
            ),
        ),
    ]


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    prompt_input = ImagePromptInput(
        image_url="https://upload.wikimedia.org/wikipedia/en/8/85/Cute_Dom_cat.JPG",
        theme="dramatic",
    )
    prompt = ImagePrompt(prompt_input)
    response = await llm.generate(prompt)
    print(response.description)


if __name__ == "__main__":
    asyncio.run(main())
