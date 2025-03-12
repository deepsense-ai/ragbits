from typing import Any

from pydantic import BaseModel

from ragbits.core.llms.base import LLM
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.document_search.documents.element import (
    Element,
    ImageElement,
    IntermediateElement,
    IntermediateImageElement,
)
from ragbits.document_search.ingestion.intermediate_handlers.base import BaseIntermediateHandler

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


class ImageIntermediateHandler(BaseIntermediateHandler):
    """
    Provides image processing capabilities using an LLM.
    """

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

    async def process(self, intermediate_element: IntermediateElement) -> Element:
        """
        Processes an intermediate image element and generates a corresponding ImageElement.

        Args:
            intermediate_element: The intermediate image element to process.

        Returns:
            The processed image element with a generated description.

        Raises:
            TypeError: If the provided element is not an IntermediateImageElement.
        """
        if not isinstance(intermediate_element, IntermediateImageElement):
            raise TypeError(f"Expected IntermediateImageElement, got {type(intermediate_element).__name__}")

        input_data = self._prompt.input_type(image=intermediate_element.image_bytes)  # type: ignore
        prompt = self._prompt(input_data)
        response = await self._llm.generate(prompt)

        return ImageElement(
            document_meta=intermediate_element.document_meta,
            description=response,
            ocr_extracted_text=intermediate_element.ocr_extracted_text,
            image_bytes=intermediate_element.image_bytes,
        )

    @classmethod
    def from_config(cls, config: dict) -> "ImageIntermediateHandler":
        """
        Create an `ImageIntermediateHandler` instance from a configuration dictionary.

        Args:
            config: A dictionary containing the configuration settings.

        Returns:
            An initialized instance of `ImageIntermediateHandler`.
        """
        llm: LLM = LLM.subclass_from_config(ObjectContructionConfig.model_validate(config["llm"]))
        return cls(llm=llm)
