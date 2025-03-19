import asyncio
from typing import Any

from pydantic import BaseModel

from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.llms.factory import get_preferred_llm
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectContructionConfig, import_by_path
from ragbits.document_search.documents.element import (
    Element,
    ImageElement,
)
from ragbits.document_search.ingestion.enrichers.base import BaseIntermediateHandler


class ImagePromptInput(BaseModel):
    """
    Represents the input for an image processing prompt.
    """

    image: bytes


class _ImagePrompt(Prompt[ImagePromptInput]):
    """
    Defines a prompt for processing image elements using an LLM.
    """

    user_prompt: str = "Describe the content of the image."
    image_input_fields: list[str] = ["image"]


class ImageIntermediateHandler(BaseIntermediateHandler):
    """
    Provides image processing capabilities using an LLM.
    """

    def __init__(self, llm: LLM | None = None, prompt: type[Prompt[ImagePromptInput, Any]] | None = None) -> None:
        """
        Initializes the ImageProvider.

        Args:
            llm: The language model to use for processing images.
            prompt: The prompt class to use.
                Defaults to `_ImagePrompt` if not provided.
        """
        self._llm = llm or get_preferred_llm(llm_type=LLMType.VISION)
        self._prompt = prompt or _ImagePrompt

    async def process(self, elements: list[Element]) -> list[Element]:
        """
        Processes a list of intermediate image elements concurrently and generates corresponding ImageElements.

        Args:
            elements: The elements to be enriched.

        Returns:
            The list of enriched elements.
        """
        tasks = [self._process_single(element) for element in elements if isinstance(element, ImageElement)]
        skipped_count = len(elements) - len(tasks)

        if skipped_count > 0:
            print(f"Warning: {skipped_count} elements were skipped due to incorrect type.")

        return await asyncio.gather(*tasks)

    async def _process_single(self, element: ImageElement) -> ImageElement:
        input_data = self._prompt.input_type(image=element.image_bytes)  # type: ignore
        prompt = self._prompt(input_data)
        response = await self._llm.generate(prompt)

        return ImageElement(
            document_meta=element.document_meta,
            description=response,
            ocr_extracted_text=element.ocr_extracted_text,
            image_bytes=element.image_bytes,
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
        prompt_cls = None
        if "prompt" in config:
            prompt_cls = import_by_path(config["prompt"])
        return cls(llm=llm, prompt=prompt_cls)
