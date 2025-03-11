from abc import ABC, abstractmethod
from typing import ClassVar, Any

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import ImageElement
from ragbits.document_search.ingestion import intermediate_providers
from ragbits.core.llms.base import LLM
from pathlib import Path

from PIL import Image
from pydantic import BaseModel
from unstructured.chunking.basic import chunk_elements
from unstructured.documents.elements import Element as UnstructuredElement
from unstructured.documents.elements import ElementType

from ragbits.core.llms.base import LLM, LLMType
from ragbits.core.llms.factory import get_preferred_llm
from ragbits.core.prompt import Prompt
from ragbits.document_search.documents.document import DocumentMeta, DocumentType
from ragbits.document_search.documents.element import Element, IntermediateImageElement


DEFAULT_IMAGE_QUESTION_PROMPT = "Describe the content of the image."


class _ImagePromptInput(BaseModel):
    image: bytes
    

class _ImagePrompt(Prompt[_ImagePromptInput]):
    user_prompt: str = DEFAULT_IMAGE_QUESTION_PROMPT
    image_input_fields: list[str] = ["image"]

    
class ImageProvider(WithConstructionConfig):
    """
    """

    default_module: ClassVar = intermediate_providers
    configuration_key: ClassVar = "intermediate_provider"
    
    def __init__(self, llm: LLM, prompt: type[Prompt[_ImagePromptInput, Any]] | None = None):
        self._llm = llm
        self._prompt = prompt or _ImagePrompt
    
    async def process(self, intermediate_image_element: IntermediateImageElement) -> ImageElement:
        """
        Process the document.

        Args:
            document_meta: The document to process.

        Returns:
            The list of elements extracted from the document.
        """

        input_data = self._prompt.input_type(image=intermediate_image_element.image_bytes)  # type: ignore
        prompt = self._prompt(input_data)
        response = await self._llm.generate(prompt)
        
        image_element = ImageElement(
            document_meta=intermediate_image_element.document_meta, 
            description=response, 
            ocr_extracted_text=intermediate_image_element.ocr_extracted_text,
            image_bytes=intermediate_image_element.image_bytes
        )
        
        return image_element