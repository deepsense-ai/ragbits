from pydantic import BaseModel

from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.llms.factory import get_preferred_llm
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectConstructionConfig, import_by_path
from ragbits.document_search.documents.element import ImageElement
from ragbits.document_search.ingestion.enrichers.base import ElementEnricher


class ImageDescriberInput(BaseModel):
    """
    Input data for an image describer prompt.
    """

    image: bytes


class ImageDescriberOutput(BaseModel):
    """
    Output data for an image describer prompt.
    """

    description: str


class ImageDescriberPrompt(Prompt[ImageDescriberInput, ImageDescriberOutput]):
    """
    Prompt for describing image elements using LLM.
    """

    user_prompt = "Describe the content of the image."
    image_input_fields = ["image"]


class ImageElementEnricher(ElementEnricher[ImageElement]):
    """
    Enricher that describes image elements using LLM.
    """

    def __init__(
        self,
        llm: LLM | None = None,
        prompt: type[Prompt[ImageDescriberInput, ImageDescriberOutput]] | None = None,
    ) -> None:
        """
        Initialize the ImageElementEnricher instance.

        Args:
            llm: The language model to use for describing images.
            prompt: The prompt class to use.
        """
        self._llm = llm or get_preferred_llm(llm_type=LLMType.VISION)
        self._prompt = prompt or ImageDescriberPrompt

    async def enrich(self, elements: list[ImageElement]) -> list[ImageElement]:
        """
        Enrich image elements with additional description of the image.

        Args:
            elements: The elements to be enriched.

        Returns:
            The list of enriched elements.

        Raises:
            EnricherElementNotSupportedError: If the element type is not supported.
            LLMError: If LLM generation fails.
        """
        responses: list[ImageDescriberOutput] = []
        for element in elements:
            self.validate_element_type(type(element))
            prompt = self._prompt(ImageDescriberInput(image=element.image_bytes))
            responses.append(await self._llm.generate(prompt))

        return [
            ImageElement(
                document_meta=element.document_meta,
                description=response.description,
                image_bytes=element.image_bytes,
                ocr_extracted_text=element.ocr_extracted_text,
            )
            for element, response in zip(elements, responses, strict=True)
        ]

    @classmethod
    def from_config(cls, config: dict) -> "ImageElementEnricher":
        """
        Create an `ImageElementEnricher` instance from a configuration dictionary.

        Args:
            config: The dictionary containing the configuration settings.

        Returns:
            The initialized instance of `ImageElementEnricher`.

        Raises:
            ValidationError: If the configuration doesn't follow the expected format.
            InvalidConfigError: If llm or prompt can't be found or are not the correct type.
        """
        config["llm"] = (
            LLM.subclass_from_config(ObjectConstructionConfig.model_validate(config["llm"]))
            if "llm" in config
            else None
        )
        config["prompt"] = import_by_path(config["prompt"]) if "prompt" in config else None
        return super().from_config(config)
