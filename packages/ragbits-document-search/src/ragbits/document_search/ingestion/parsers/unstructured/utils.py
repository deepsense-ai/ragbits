import io
import os
import warnings as wrngs

from PIL import Image
from unstructured.documents.elements import Element as UnstructuredElement

from ragbits.core.llms.base import LLM
from ragbits.core.prompt.base import BasePrompt
from ragbits.document_search.documents.document import DocumentMeta
from ragbits.document_search.documents.element import ElementLocation, TextElement


def to_text_element(element: UnstructuredElement, document_meta: DocumentMeta) -> TextElement:
    """
    Converts unstructured element to ragbits text element

    Args:
        element: element from unstructured
        document_meta: metadata of the document

    Returns:
        text element
    """
    location = to_element_location(element)
    return TextElement(
        document_meta=document_meta,
        content=element.text,
        location=location,
    )


def to_element_location(element: UnstructuredElement) -> ElementLocation:
    """
    Converts unstructured element to element location.

    Args:
        element: element from unstructured

    Returns:
        element location
    """
    metadata = element.metadata.to_dict()
    page_number = metadata.get("page_number")
    coordinates = metadata.get("coordinates")
    return ElementLocation(
        page_number=page_number,
        coordinates=coordinates,
    )


def check_required_argument(value: str | None, arg_name: str, fallback_env: str) -> str:
    """
    Checks if given environment variable is set and returns it or raises an error

    Args:
        arg_name: name of the variable
        value: optional default value
        fallback_env: name of the environment variable to get

    Raises:
        ValueError: if environment variable is not set

    Returns:
        environment variable value
    """
    if value is not None:
        return value
    if (env_value := os.getenv(fallback_env)) is None:
        raise ValueError(f"Either pass {arg_name} argument or set the {fallback_env} environment variable")
    return env_value


def extract_image_coordinates(element: UnstructuredElement) -> tuple[float, float, float, float]:
    """
    Extracts image coordinates from unstructured element
    Args:
        element: element from unstructured
    Returns:
        x of top left corner, y of top left corner, x of bottom right corner, y of bottom right corner
    """
    p1, p2, p3, p4 = element.metadata.coordinates.points  # type: ignore
    return min(p1[0], p2[0]), min(p1[1], p4[1]), max(p3[0], p4[0]), max(p2[1], p3[1])


def crop_and_convert_to_bytes(image: Image.Image, x0: float, y0: float, x1: float, y1: float) -> bytes:
    """
    Crops the image and converts to bytes
    Args:
        image: PIL image
        x0: x of top left corner
        y0: y of top left corner
        x1: x of bottom right corner
        y1: y of bottom right corner
    Returns:
        bytes of the cropped image
    """
    image = image.crop((x0, y0, x1, y1))
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return buffered.getvalue()


class ImageDescriber:
    """
    Describes images content using an LLM
    """

    def __init__(self, llm: LLM):
        self.llm = llm

    async def get_image_description(self, prompt: BasePrompt) -> str:
        """
        Provides summary of the image passed with prompt

        Args:
            prompt: BasePrompt an instance of a prompt
        Returns:
            summary of the image
        """
        if not prompt.list_images():
            wrngs.warn(message="Image data not provided", category=UserWarning)
        return await self.llm.generate(prompt=prompt)
