# How to define and use image prompts in Ragbits

This guide will walk you through defining and using prompts in Ragbits that accept images as input. It covers handling single and multiple image inputs, incorporating conditionals in prompt templates based on the presence of images, and using such prompts with an LLM.

## How to define a prompt with an image input

### Using a single image as input

To define a prompt that takes a single image as input, create a Pydantic model representing the input structure. The model should include an image field, which is either a **URL pointing to the image** or a **base64-encoded string**.

```python
import asyncio
from pydantic import BaseModel
from ragbits.core.prompt import Prompt
from ragbits.core.llms.litellm import LiteLLM


class ImagePromptInput(BaseModel):
    """
    Input model containing a single image.
    """
    image: bytes | str


class ImagePrompt(Prompt):
    """
    A prompt for generating a caption from an image.
    """

    user_prompt = "What is on this image?"
    image_input_fields = ["image"]


async def main():
    llm = LiteLLM("gpt-4o")
    prompt = ImagePrompt(ImagePromptInput(image="<your_image_here>"))
    response = await llm.generate(prompt)
    print(response)


asyncio.run(main())
```

### Using multiple images as input

If you need a prompt that accepts multiple images, define an input model containing a list of image strings.

```python
class ImagesPromptInput(BaseModel):
    """
    Input model containing multiple images.
    """
    images: list[bytes | str]


class ImagesPrompt(Prompt):
    """
    A prompt for generating descriptions from multiple images.
    """

    user_prompt = "What is on these images?"
    image_input_fields = ["images"]


async def main():
    llm = LiteLLM("gpt-4o")
    images = [
        "<your_image_1_here>",
        "<your_image_2_here>",
    ]
    prompt = ImagesPrompt(ImagesPromptInput(images=images))
    response = await llm.generate(prompt)
    print(response)


asyncio.run(main())
```

## Using conditionals in templates

Sometimes, you may want to modify the prompt based on whether an image is provided. Jinja conditionals can help achieve this.

```python
class OptionalImagePromptInput(BaseModel):
    """
    Input model that optionally includes an image.
    """
    query: str
    image: bytes | str | None = None


class OptionalImagePrompt(Prompt[OptionalImagePromptInput]):
    """
    A prompt that considers whether an image is provided.
    """

    system_prompt = """
    You are a knowledgeable assistant that answers queries.
    If an image is provided, consider its content in your response.
    """

    user_prompt = """
    User asked: {{ query }}
    {% if image %}
    Here is an image that may help: {{ image }}
    {% else %}
    No image was provided.
    {% endif %}
    """

    image_input_fields = ["image"]


async def main():
    llm = LiteLLM("gpt-4o")
    input_with_image = OptionalImageInput(query="What is in this image?", image="<your_image_here>")
    input_without_image = OptionalImageInput(query="What is the capital of France?")

    print(await llm.generate(OptionalImagePrompt(input_with_image)))
    print(await llm.generate(OptionalImagePrompt(input_without_image)))


asyncio.run(main())
```
