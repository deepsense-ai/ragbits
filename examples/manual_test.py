import asyncio

import pydantic

from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Prompt


class ImagePromptInput(pydantic.BaseModel):
    """
    Input format for the TestImagePrompt.
    """

    image: bytes | str | None


def _get_image_bytes() -> bytes:
    """Get the test image as bytes."""
    with open(
        "/home/konrad/Desktop/ragbits_project/ragbits/packages/ragbits-core/tests/test-images/test.png", "rb"
    ) as f:
        return f.read()


class ImagePrompt(Prompt):
    user_prompt = "What is on this image? Use the tone similar to the one in provided examples"
    image_input_fields = ["image"]
    few_shots = [(ImagePromptInput(image=_get_image_bytes()), "Arr! That's a cat, my pirate!")]


async def run():
    llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
    prompt = ImagePrompt(ImagePromptInput(image=_get_image_bytes()))
    # prompt.add_few_shot(ImagePromptInput(image="https://example.com/image.jpg"), "A picture of a cat.")#image=_get_image_bytes()), "A picture of a cat.")
    # print(len(prompt.chat))
    # print(prompt.chat)
    # print(len(prompt.list_images()))
    response = await llm.generate(prompt)
    print(response)


if __name__ == "__main__":
    asyncio.run(run())

    # from chromadb import PersistentClient

    # client = PersistentClient('chroma')
    # collections = client.list_collections()
    # for collection in collections:
    #    print(collection)
    # collection = client.get_or_create_collection(
    #        name="documents",
    #    )

    # Retrieve all data
    # print(collection.count())
    # print(collection.peek())

    # asyncio.run(main())
    # elems = partition_html("/home/konrad/Desktop/hex_topaz/fluid_topics/introduction.html")
    # chunking_kwargs = {}
    # chunked_elements = chunk_elements(elems, **chunking_kwargs)
    # print(chunked_elements)
