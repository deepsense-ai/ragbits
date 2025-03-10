# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
# ]
# ///
import asyncio

import pydantic

from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class ImagePromptInput(pydantic.BaseModel):
    """
    Input format for the ImagePrompt input.
    """

    image_url: str = None
    theme: str


class ImagePrompt(Prompt[ImagePromptInput]):
    """
    A prompt that generates descriptions of images.
    """

    user_prompt = "What is on this image? Use the this theme: {{ theme }} to make the answer more personal."
    image_input_fields = ["image_url"]


async def main() -> None:
    """
    Example of using the LiteLLM client with a multimodal input  in prompt. Requires the OPENAI_API_KEY environment
    variable to be set.
    """
    llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
    prompt = ImagePrompt(
        ImagePromptInput(image_url="https://upload.wikimedia.org/wikipedia/en/8/85/Cute_Dom_cat.JPG", theme="cute")
    )
    prompt.add_few_shot(
        ImagePromptInput(
            image_url="https://upload.wikimedia.org/wikipedia/commons/5/55/Acd_a_frame.jpg", theme="pirates"
        ),
        "Arrr, that would be a dog!.",
    )
    response = await llm.generate(prompt)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
