# Use images in prompts

This guide will walk you through defining and using prompts in Ragbits that accept images as input. It covers handling single and multiple image inputs, incorporating conditionals in prompt templates based on the presence of images, and using such prompts with an LLM.

## How to define a prompt with an image input

### Using a single image as input

To define a prompt that takes a single image as input, create a Pydantic model representing the input structure. The model should include a field for the image, which can be a **URL pointing to the image** or a **base64-encoded string**.

```python
import asyncio
from pydantic import BaseModel
from ragbits.core.prompt import Prompt
from ragbits.core.llms.litellm import LiteLLM


class AnimalPhotoInput(BaseModel):
    """
    Input model containing a single animal photo.
    """
    photo: bytes | str


class AnimalPhotoPrompt(Prompt):
    """
    A prompt for identifying an animal in a photo.
    """

    user_prompt = "What animal do you see in this photo?"
    image_input_fields = ["photo"]


async def main():
    llm = LiteLLM("gpt-4o")
    prompt = AnimalPhotoPrompt(AnimalPhotoInput(photo="<your_photo_here>"))
    response = await llm.generate(prompt)
    print(response)


asyncio.run(main())
```

### Using multiple images as input

If you need a prompt that accepts multiple images, define an input model containing a list of image fields, which can be a list of URLs pointing to the images or a list of base64-encoded strings representing the images.

```python
class AnimalGalleryInput(BaseModel):
    """
    Input model containing multiple animal photos.
    """
    photos: list[bytes | str]


class AnimalGalleryPrompt(Prompt):
    """
    A prompt for identifying animals in multiple photos.
    """

    user_prompt = "What animals do you see in these photos?"
    image_input_fields = ["photos"]


async def main():
    llm = LiteLLM("gpt-4o")
    photos = [
        "<your_photo_1_here>",
        "<your_photo_2_here>",
    ]
    prompt = AnimalGalleryPrompt(AnimalGalleryInput(photos=photos))
    response = await llm.generate(prompt)
    print(response)


asyncio.run(main())
```

## Using conditionals in templates

Sometimes, you may want to modify the prompt based on whether an image is provided. Jinja conditionals can help achieve this.

```python
class QuestionWithOptionalPhotoInput(BaseModel):
    """
    Input model that optionally includes a photo.
    """
    question: str
    reference_photo: bytes | str | None = None


class QuestionWithPhotoPrompt(Prompt[QuestionWithOptionalPhotoInput]):
    """
    A prompt that considers whether a photo is provided.
    """

    system_prompt = """
    You are a knowledgeable assistant providing detailed answers.
    If a photo is provided, use it as a reference for your response.
    """

    user_prompt = """
    User asked: {{ question }}
    {% if reference_photo %}
    Here is a reference photo: {{ reference_photo }}
    {% else %}
    No photo was provided.
    {% endif %}
    """

    image_input_fields = ["reference_photo"]


async def main():
    llm = LiteLLM("gpt-4o")
    input_with_photo = QuestionWithOptionalPhotoInput(question="What animal do you see in this photo?", reference_photo="<your_photo_here>")
    input_without_photo = QuestionWithOptionalPhotoInput(question="What is the capital of France?")

    print(await llm.generate(QuestionWithPhotoPrompt(input_with_photo)))
    print(await llm.generate(QuestionWithPhotoPrompt(input_without_photo)))


asyncio.run(main())
```