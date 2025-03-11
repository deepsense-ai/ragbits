from typing import Any, ClassVar

from pydantic import BaseModel

from ragbits.core.llms.base import LLM
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.element import ImageElement, IntermediateImageElement
from ragbits.document_search.ingestion import intermediate_providers

DEFAULT_IMAGE_QUESTION_PROMPT = "Describe the content of the image."


class _ImagePromptInput(BaseModel):
    """
    Represents the input for an image processing prompt.
    """

    image: bytes


class _ImagePrompt(Prompt[_ImagePromptInput]):
    """
    Defines a prompt for processing image elements using an LLM.
    """

    user_prompt: str = DEFAULT_IMAGE_QUESTION_PROMPT
    image_input_fields: list[str] = ["image"]


class ImageProvider(WithConstructionConfig):
    """
    Provides image processing capabilities using an LLM.
    """

    default_module: ClassVar = intermediate_providers
    configuration_key: ClassVar = "intermediate_provider"

    def __init__(self, llm: LLM, prompt: type[Prompt[_ImagePromptInput, Any]] | None = None):
        """
        Initializes the ImageProvider.

        Args:
            llm: The language model to use for processing images.
            prompt: The prompt class to use.
                Defaults to `_ImagePrompt` if not provided.
        """
        self._llm = llm
        self._prompt = prompt or _ImagePrompt

    async def process(self, intermediate_image_element: IntermediateImageElement) -> ImageElement:
        """
        Processes an intermediate image element and generates a corresponding ImageElement.

        Args:
            intermediate_image_element: The intermediate image element to process.

        Returns:
            The processed image element with a generated description.
        """
        input_data = self._prompt.input_type(image=intermediate_image_element.image_bytes)  # type: ignore
        prompt = self._prompt(input_data)
        response = await self._llm.generate(prompt)

        image_element = ImageElement(
            document_meta=intermediate_image_element.document_meta,
            description=response,
            ocr_extracted_text=intermediate_image_element.ocr_extracted_text,
            image_bytes=intermediate_image_element.image_bytes,
        )

        return image_element
